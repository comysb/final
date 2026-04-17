# -*- coding: utf-8 -*-
"""
severity_app/app.py
- 목적: 마비말장애 '중증도 진단' 전용 FastAPI 서버
- 실행: uvicorn app:app --reload --port 8000
"""

import os
import glob
import json
import joblib
import torch
import uuid
import shutil
import warnings
import numpy as np
from pathlib import Path
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from xgboost import XGBClassifier

import acoustic_utils as utils

warnings.filterwarnings("ignore")

# =====================================================================
# 모델 경로 설정
# =====================================================================
class MODEL_CONFIG:
    MODELS_DIR = "models"
    XGB_MODEL       = os.path.join(MODELS_DIR, "final_xgb_model.json")
    HEALTHY_STATS   = os.path.join(MODELS_DIR, "healthy_stats.joblib")
    PITCH_STATS     = os.path.join(MODELS_DIR, "pitch_stats.joblib")
    WAV2VEC2_MODEL  = os.path.join(MODELS_DIR, "wav2vec2_acoustic")

    FEATURE_COLS = [
        "jitter", "shimmer", "apq",
        "crr", "vrr", "prr",
        "mean_f0", "median_f0", "min_f0", "max_f0",
        "mean_energy", "median_energy", "std_energy", "min_energy", "max_energy",
        "vsa_triangle", "fcr", "vai", "f2_ratio",
    ]

# =====================================================================
# 재활 솔루션 추천 (중증도 기반 간단 추천)
# =====================================================================
THERAPY_EXERCISES = {
    "posture_correction":  {"id": 1,  "name": "자세 교정",           "desc": "바른 자세로 발성 호흡 지지력 확보",         "category": "respiration_phonation"},
    "breathing":           {"id": 12, "name": "호흡 훈련",            "desc": "깊은 숨을 내쉬는 호흡 훈련",               "category": "respiration_phonation"},
    "sustained_phonation": {"id": 3,  "name": "목표음 연장 발성",     "desc": "목표음을 최대한 길고 크게 발성",            "category": "respiration_phonation"},
    "effortful_closure":   {"id": 8,  "name": "성대 내전 운동",       "desc": "성대를 강하게 접촉시키는 훈련",             "category": "respiration_phonation"},
    "oral_motor":          {"id": 2,  "name": "구강 운동",            "desc": "조음 기관 가동 범위 확장",                 "category": "articulation_resonance"},
    "contrast_drills":     {"id": 10, "name": "최소 대립쌍 읽기",     "desc": "미세한 발음 차이를 구분하여 읽기",          "category": "articulation_resonance"},
    "gliding_up":          {"id": 4,  "name": "피치 올리기",          "desc": "발성하며 피치를 위로 끌어올림",             "category": "prosody"},
    "pitch_control":       {"id": 6,  "name": "피치 조절 반복",       "desc": "올렸다 내리는 피치 반복 훈련",             "category": "prosody"},
    "slow_reading":        {"id": 14, "name": "속도 조절",            "desc": "일정하게 느린 목표 속도 유지하며 읽기",     "category": "prosody"},
}

class RehabSolutionGenerator:
    def __init__(self):
        self.groups = {
            "respiration_phonation":   ["jitter", "shimmer", "apq", "mean_energy", "median_energy", "std_energy", "min_energy", "max_energy"],
            "articulation_resonance":  ["crr", "vrr", "prr", "vsa_triangle", "fcr", "vai", "f2_ratio"],
            "prosody":                 ["mean_f0", "median_f0", "min_f0", "max_f0"],
        }

    def generate_solution(self, t_vals, severity):
        scores = {}
        for cat, feats in self.groups.items():
            vs = [t_vals[f] for f in feats if f in t_vals]
            scores[cat] = round(float(np.mean(vs)) * 100.0, 1) if vs else 100.0

        sev = severity.lower()
        if "severe" in sev or "고도" in sev:
            intensity = {"level": "저강도 분할", "sets": 3, "reps": 3, "duration": "15분 씩 3회", "focus": "기초 호흡 및 구강 운동", "color_theme": "danger"}
        elif any(k in sev for k in ["mild", "moderate", "중등도", "경도"]):
            intensity = {"level": "강화",       "sets": 3, "reps": 10, "duration": "하루 20~30분", "focus": "취약 영역 적극 개선",    "color_theme": "warning"}
        else:
            intensity = {"level": "유지",       "sets": 1, "reps": 5,  "duration": "하루 10분 이내","focus": "발성 및 가동범위 유지",  "color_theme": "success"}

        weakest = sorted(scores.items(), key=lambda x: x[1])[0][0]
        selected = [ex for ex in THERAPY_EXERCISES.values() if ex["category"] == weakest][:3]
        if len(selected) < 4:
            selected.append(THERAPY_EXERCISES["posture_correction"])

        return {"health_scores": scores, "intensity_plan": intensity, "recommended_exercises": selected[:4]}

# =====================================================================
# 추론 엔진
# =====================================================================
class InferenceEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Init] 디바이스: {self.device}")

        self.healthy_stats = joblib.load(MODEL_CONFIG.HEALTHY_STATS)
        self.pitch_stats   = joblib.load(MODEL_CONFIG.PITCH_STATS)
        self.xgb_model     = XGBClassifier()
        self.xgb_model.load_model(MODEL_CONFIG.XGB_MODEL)

        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        self.processor = Wav2Vec2Processor.from_pretrained(MODEL_CONFIG.WAV2VEC2_MODEL)
        self.model     = Wav2Vec2ForCTC.from_pretrained(MODEL_CONFIG.WAV2VEC2_MODEL).to(self.device).eval()
        self.vocab     = self.processor.tokenizer.get_vocab()

        self.mfa_dict  = utils.load_mfa_dictionary(utils.MFA_DICT_PATH)
        self.can_all, self.can_cons, self.can_vows = utils.build_canonical_sequence(utils.DEFAULT_WORDS, self.mfa_dict)
        self.word_order = {w: i for i, w in enumerate(utils.DEFAULT_WORDS)}

    def analyze_audio_folder(self, folder, sex, age):
        files = glob.glob(os.path.join(folder, "*.wav"))
        segments = []
        for p in files:
            base = os.path.splitext(os.path.basename(p))[0]
            word = next((w for w in utils.DEFAULT_WORDS if w in base), None)
            if word:
                segments.append((word, self.word_order[word], p))
        segments.sort(key=lambda x: x[1])

        word_feats = {c: [] for c in MODEL_CONFIG.FEATURE_COLS if c not in ["crr","vrr","prr","vsa_triangle","fcr","vai","f2_ratio"]}
        vow_data = {"I": [], "U": [], "A": []}
        clips = []

        sex_key = str(sex).strip().upper()
        max_f = 5500.0 if sex_key not in ["M", "남", "MALE", "1"] else 5000.0

        for word, _, path in segments:
            clip = utils.load_and_trim_clip(path)
            if clip is not None:
                clips.append(clip)
                clips.append(np.zeros(int(0.05 * 16000), dtype=np.float32))

            vq = utils.extract_voice_quality(path)
            pi = utils.extract_pitch_features(path)
            en = utils.extract_energy_features(path)
            for d in [vq, pi, en]:
                for k, v in d.items():
                    if k in word_feats:
                        word_feats[k].append(v)

            al = utils.align_word(path, word, self.model, self.vocab, self.mfa_dict, self.device)
            for ph in al.get("alignment", []):
                sym = utils.IPA_TO_SLPLAB.get(ph["phoneme"], ph["phoneme"])
                if sym in vow_data and (ph["end"] - ph["start"]) >= 0.03:
                    f1, f2 = utils.extract_formant_at_midpoint(path, ph["start"], ph["end"], max_f)
                    if f1:
                        vow_data[sym].append((f1, f2))

        if clips:
            pred_all = utils.decode_slplab(np.concatenate(clips), self.processor, self.model, self.device)
            p_cons   = [p for p in pred_all if p in utils.CONSONANTS]
            p_vows   = [p for p in pred_all if p in utils.VOWELS]
            crr = utils.calc_correct_rate(self.can_cons, p_cons)
            vrr = utils.calc_correct_rate(self.can_vows, p_vows)
            prr = utils.calc_correct_rate(self.can_all, pred_all)
        else:
            crr = vrr = prr = 0.0

        vsa = utils.compute_vsa_metrics(vow_data)

        raw = {}
        for c in MODEL_CONFIG.FEATURE_COLS:
            if c in word_feats:
                val = np.nanmean(word_feats[c]) if word_feats[c] else 0.0
                if "f0" in c:
                    ref = self.pitch_stats.get(c, {}).get((sex, "young"), {"mean": 0, "std": 1})
                    val = (val - ref["mean"]) / (ref["std"] + 1e-9)
                raw[c] = val
            elif c in vsa:  raw[c] = vsa[c] if not np.isnan(vsa[c]) else 0.0
            elif c == "crr": raw[c] = crr
            elif c == "vrr": raw[c] = vrr
            elif c == "prr": raw[c] = prr

        transformed = []
        t_val_dict  = {}
        for col in MODEL_CONFIG.FEATURE_COLS:
            v  = raw.get(col, 0.0)
            st = self.healthy_stats.get(col, {"mean": 0.0, "std": 1.0})
            diff = abs(v - st["mean"])
            t    = (st["std"] / diff) if diff > st["std"] else 1.0
            transformed.append(t)
            t_val_dict[col] = t

        X    = np.array([transformed])
        pred = self.xgb_model.predict(X)[0]
        prob = self.xgb_model.predict_proba(X)[0]
        cmap = {0: "정상 (Normal)", 1: "경도-중등도 (Mild-to-Moderate)", 2: "고도 (Severe)"}

        return {
            "prediction": {
                "severity_label":  cmap[int(pred)],
                "confidence_score": float(np.max(prob)),
                "probabilities":    {cmap[i]: float(prob[i]) for i in range(3)},
            },
            "metrics": {
                "pronunciation": {"prr": round(prr, 2), "crr": round(crr, 2)},
                "voice":         {"jitter": round(np.nanmean(word_feats["jitter"]), 5) if word_feats["jitter"] else 0},
            },
            "t_vals": t_val_dict,
        }

# =====================================================================
# FastAPI 앱
# =====================================================================
app = FastAPI(title="말길 - 중증도 진단 서버")

BASE_DIR  = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

print("[APP] 중증도 진단 엔진 초기화 중...")
engine  = InferenceEngine()
sol_gen = RehabSolutionGenerator()

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/diagnose")
async def diagnose(age: int = Form(...), sex: str = Form(...), files: list[UploadFile] = File(...)):
    try:
        req_id = str(uuid.uuid4())
        tmp    = os.path.join("temp_audio", req_id)
        os.makedirs(tmp, exist_ok=True)

        for f in files:
            stem = Path(f.filename).stem
            p    = os.path.join(tmp, f"{stem}.wav")
            b    = await f.read()
            with open(os.path.join(tmp, f.filename), "wb") as buf:
                buf.write(b)
            if not f.filename.endswith(".wav"):
                import librosa, soundfile as sf
                y, sr = librosa.load(os.path.join(tmp, f.filename), sr=16000)
                sf.write(p, y, sr)
            else:
                os.rename(os.path.join(tmp, f.filename), p)

        report = engine.analyze_audio_folder(tmp, sex, age)
        if "t_vals" in report:
            report["solution"] = sol_gen.generate_solution(report["t_vals"], report["prediction"]["severity_label"])
            del report["t_vals"]

        shutil.rmtree(tmp, ignore_errors=True)
        return JSONResponse(content={"status": "success", "data": report})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

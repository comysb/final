"""
말길 FastAPI 백엔드 v3
- 퍼터커(DDK)  : ResNet+Fusion+MLP 마스터 모델
- 모음(아/이/우): 15D Cascade-SVM 마스터 모델
- 단어         : XGBoost + Wav2Vec2 음소 정렬 모델
"""
import os
import sys
import glob
import json
import pickle
import tempfile
import shutil
import importlib.util
import numpy as np
import torch
import librosa
import soundfile as sf
import joblib
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import warnings
warnings.filterwarnings("ignore")

# ── 경로 설정 ────────────────────────────────────────────────
PUTTERKER_DIR = r"D:\퍼터커"
AIIU_DIR      = r"D:\아이우"
WORD_DIR      = r"D:\단어"
MODEL_DIR     = os.path.join(PUTTERKER_DIR, "models", "master")
WORD_MODEL_DIR = os.path.join(WORD_DIR, "models")
DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"

# ── 모듈 동적 임포트 헬퍼 ───────────────────────────────────
def _load_module(name, filepath):
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# ── 앱 생성 ─────────────────────────────────────────────────
app = FastAPI(title="말길 API v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 전역 엔진 싱글턴 ─────────────────────────────────────────
_putterker_engine = None
_aiiu_engine      = None
_word_engine      = None

# ────────────────────────────────────────────────────────────
# 1. 퍼터커 엔진 (ResNet + Fusion + MLP)
# ────────────────────────────────────────────────────────────
class PutterkerEngine:
    def __init__(self):
        print("[퍼터커] 모듈 로드 중...")
        if PUTTERKER_DIR not in sys.path:
            sys.path.insert(0, PUTTERKER_DIR)

        self.m_enc  = _load_module("m_enc",  os.path.join(PUTTERKER_DIR, "03_deep_encoders.py"))
        self.m_fus  = _load_module("m_fus",  os.path.join(PUTTERKER_DIR, "04_attention_fusion.py"))
        self.m_cls  = _load_module("m_cls",  os.path.join(PUTTERKER_DIR, "05-1_train_classifier.py"))
        self.m_feat = _load_module("m_feat", os.path.join(PUTTERKER_DIR, "02_feature_extraction.py"))

        print("[퍼터커] 스케일러 & 임계값 로드 중...")
        with open(os.path.join(MODEL_DIR, "scaler_master.pkl"), "rb") as f:
            self.scaler = pickle.load(f)
        with open(os.path.join(MODEL_DIR, "thresholds.json"), "r", encoding="utf-8") as f:
            self.thresholds = json.load(f)

        print("[퍼터커] PyTorch 모델 로드 중...")
        self.resnet     = self.m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)
        self.fusion     = self.m_fus.FeatureFusion(ddk_dim=12, w2v_dim=256, mel_dim=256, fusion_dim=256).to(DEVICE)
        self.classifier = self.m_cls.DysarthriaMLPClassifier(input_dim=self.fusion.total_dim, num_classes=3).to(DEVICE)

        self.resnet.load_state_dict(torch.load(os.path.join(MODEL_DIR, "resnet_master.pt"), map_location=DEVICE))
        self.fusion.load_state_dict(torch.load(os.path.join(MODEL_DIR, "fusion_master.pt"), map_location=DEVICE))
        self.classifier.load_state_dict(torch.load(os.path.join(MODEL_DIR, "classifier_master.pt"), map_location=DEVICE))
        self.resnet.eval(); self.fusion.eval(); self.classifier.eval()

        print("[퍼터커] LSTM 음절분할기 로드 중...")
        self.lstm_model = self.m_feat.get_lstm_model(device=DEVICE)
        print("[퍼터커] 엔진 준비 완료!")

    def predict(self, wav_path: str) -> dict:
        with torch.no_grad():
            ddk_feats = self.m_feat.extract_all_features(wav_path, lstm_model=self.lstm_model, device=DEVICE)
            ddk_cols  = [
                "f0_var_hz", "f0_var_semitones",
                "mean_energy_db", "var_energy_db", "max_energy_db",
                "ddk_rate", "ddk_mean_dur_ms", "ddk_regularity_ms",
                "pause_rate", "pause_mean_dur_ms", "pause_regularity_ms",
                "intelligibility_score",
            ]
            ddk_arr    = np.array([ddk_feats.get(c, 0.0) for c in ddk_cols], dtype=np.float32).reshape(1, -1)
            ddk_scaled = self.scaler.transform(ddk_arr)
            ddk_tensor = torch.FloatTensor(ddk_scaled).to(DEVICE)

            mel_tensor = self.m_cls.my_audio_to_mel(wav_path, is_train=False).unsqueeze(0).to(DEVICE)
            mel_emb    = self.resnet(mel_tensor)
            w2v_emb    = torch.zeros(1, 256).to(DEVICE)
            gender_t   = torch.zeros(1, 1).to(DEVICE)

            fused  = self.fusion(ddk_tensor, gender_t, mel_emb, w2v_emb)
            logits = self.classifier(fused)
            probs  = torch.softmax(logits, dim=1).cpu().numpy()[0]

        prob_anomaly  = float(probs[1] + probs[2])
        thresh_binary = self.thresholds.get("thresh_binary", 0.5)
        thresh_severe = self.thresholds.get("thresh_severe", 0.5)

        if prob_anomaly < thresh_binary:
            severity_class = 0
        else:
            severe_ratio   = float(probs[2]) / (prob_anomaly + 1e-8)
            severity_class = 2 if severe_ratio >= thresh_severe else 1

        label_map = {0: "정상", 1: "경증", 2: "중증"}
        return {
            "severity_class": severity_class,
            "severity_label": label_map[severity_class],
            "probs": {
                "정상": round(float(probs[0]), 4),
                "경증": round(float(probs[1]), 4),
                "중증": round(float(probs[2]), 4),
            },
            "features": {k: round(float(v), 4) for k, v in ddk_feats.items()},
        }


# ────────────────────────────────────────────────────────────
# 2. 아이우 엔진 (15D Cascade-SVM)
# ────────────────────────────────────────────────────────────
class AiiuEngine:
    def __init__(self):
        print("[아이우] 15D Cascade-SVM 엔진 로드 중...")
        # 아이우 pipeline 패키지를 sys.path에 추가
        if AIIU_DIR not in sys.path:
            sys.path.insert(0, AIIU_DIR)

        from pipeline.inference_engine import DysarthriaInferenceEngine
        self.engine = DysarthriaInferenceEngine()
        print("[아이우] 엔진 준비 완료!")

    def predict(self, path_a: str, path_i: str, path_u: str) -> dict:
        result = self.engine.predict(path_a, path_i, path_u)
        severity_class = result.get("recommended_result", 0)
        label_map = {0: "정상", 1: "경증", 2: "중증"}
        probs = result.get("class_probabilities", {"정상": 0.0, "경증": 0.0, "중증": 0.0})
        # 아이우 엔진은 % 단위로 반환 → 0~1로 정규화
        return {
            "severity_class": severity_class,
            "severity_label": label_map.get(severity_class, "정상"),
            "probs": {
                "정상": round(probs.get("정상", 0) / 100, 4),
                "경증": round(probs.get("경증", 0) / 100, 4),
                "중증": round(probs.get("중증", 0) / 100, 4),
            },
        }


# ────────────────────────────────────────────────────────────
# 3. 단어 엔진 (XGBoost + Wav2Vec2 음소 정렬)
# ────────────────────────────────────────────────────────────
class WordEngine:
    """
    D:\단어 의 XGBoost(final_xgb_model.json) + Wav2Vec2 음소 정렬 기반
    단어 발화 중증도 분류 엔진.
    입력 : 단어 wav 파일 목록 + sex(M/F) + age(int)
    출력 : severity_class(0/1/2), severity_label, probs, metrics
    """
    FEATURE_COLS = [
        "jitter", "shimmer", "apq",
        "crr", "vrr", "prr",
        "mean_f0", "median_f0", "min_f0", "max_f0",
        "mean_energy", "median_energy", "std_energy", "min_energy", "max_energy",
        "vsa_triangle", "fcr", "vai", "f2_ratio",
    ]

    def __init__(self):
        print("[단어] 모델 로드 중...")
        if WORD_DIR not in sys.path:
            sys.path.insert(0, WORD_DIR)

        # acoustic_utils 동적 임포트
        self.utils = _load_module("word_acoustic_utils",
                                  os.path.join(WORD_DIR, "acoustic_utils.py"))

        # XGBoost 모델
        from xgboost import XGBClassifier
        self.xgb = XGBClassifier()
        self.xgb.load_model(os.path.join(WORD_MODEL_DIR, "final_xgb_model.json"))

        # 정규화 통계
        self.healthy_stats = joblib.load(os.path.join(WORD_MODEL_DIR, "healthy_stats.joblib"))
        self.pitch_stats   = joblib.load(os.path.join(WORD_MODEL_DIR, "pitch_stats.joblib"))

        # Wav2Vec2 (음소 정렬용)
        print("[단어] Wav2Vec2 로드 중 (시간 소요)...")
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        w2v_path = os.path.join(WORD_MODEL_DIR, "wav2vec2_acoustic")
        self.processor = Wav2Vec2Processor.from_pretrained(w2v_path)
        self.w2v_model = Wav2Vec2ForCTC.from_pretrained(w2v_path).to(DEVICE).eval()
        self.vocab = self.processor.tokenizer.get_vocab()

        # MFA 사전 & 정준 음소열
        u = self.utils
        self.mfa_dict = u.load_mfa_dictionary(u.MFA_DICT_PATH)
        self.can_all, self.can_cons, self.can_vows = \
            u.build_canonical_sequence(u.DEFAULT_WORDS, self.mfa_dict)
        self.word_order = {w: i for i, w in enumerate(u.DEFAULT_WORDS)}
        print("[단어] 엔진 준비 완료!")

    def predict(self, wav_paths: list, sex: str, age: int) -> dict:
        """wav 파일 경로 리스트 → 단어 모델 추론 결과 반환"""
        u = self.utils
        sex_key = str(sex).strip().upper()
        max_f   = 5000.0 if sex_key in ["M", "남", "MALE", "1"] else 5500.0

        # 파일을 단어 순서로 정렬
        segments = []
        for p in wav_paths:
            base = os.path.splitext(os.path.basename(p))[0]
            word = next((w for w in u.DEFAULT_WORDS if w in base), None)
            if word:
                segments.append((word, self.word_order[word], p))
        segments.sort(key=lambda x: x[1])

        non_vow_cols = [c for c in self.FEATURE_COLS
                        if c not in ["crr","vrr","prr","vsa_triangle","fcr","vai","f2_ratio"]]
        word_feats = {c: [] for c in non_vow_cols}
        vow_data   = {"I": [], "U": [], "A": []}
        clips      = []

        for word, _, path in segments:
            clip = u.load_and_trim_clip(path)
            if clip is not None:
                clips.append(clip)
                clips.append(np.zeros(int(0.05 * 16000), dtype=np.float32))

            for feat_fn in [u.extract_voice_quality, u.extract_pitch_features, u.extract_energy_features]:
                d = feat_fn(path)
                for k, v in d.items():
                    if k in word_feats:
                        word_feats[k].append(v)

            al = u.align_word(path, word, self.w2v_model, self.vocab, self.mfa_dict, DEVICE)
            for ph in al.get("alignment", []):
                sym = u.IPA_TO_SLPLAB.get(ph["phoneme"], ph["phoneme"])
                if sym in vow_data and (ph["end"] - ph["start"]) >= 0.03:
                    f1, f2 = u.extract_formant_at_midpoint(path, ph["start"], ph["end"], max_f)
                    if f1:
                        vow_data[sym].append((f1, f2))

        if clips:
            pred_all = u.decode_slplab(np.concatenate(clips), self.processor, self.w2v_model, DEVICE)
            p_cons   = [p for p in pred_all if p in u.CONSONANTS]
            p_vows   = [p for p in pred_all if p in u.VOWELS]
            crr = u.calc_correct_rate(self.can_cons, p_cons)
            vrr = u.calc_correct_rate(self.can_vows, p_vows)
            prr = u.calc_correct_rate(self.can_all, pred_all)
        else:
            crr = vrr = prr = 0.0

        vsa = u.compute_vsa_metrics(vow_data)

        raw = {}
        for c in self.FEATURE_COLS:
            if c in word_feats:
                val = np.nanmean(word_feats[c]) if word_feats[c] else 0.0
                if "f0" in c:
                    ref = self.pitch_stats.get(c, {}).get(
                        (sex_key, "young"), {"mean": 0, "std": 1})
                    val = (val - ref["mean"]) / (ref["std"] + 1e-9)
                raw[c] = val
            elif c in vsa:   raw[c] = vsa[c] if not np.isnan(vsa[c]) else 0.0
            elif c == "crr": raw[c] = crr
            elif c == "vrr": raw[c] = vrr
            elif c == "prr": raw[c] = prr

        transformed, t_dict = [], {}
        for col in self.FEATURE_COLS:
            v  = raw.get(col, 0.0)
            st = self.healthy_stats.get(col, {"mean": 0.0, "std": 1.0})
            diff = abs(v - st["mean"])
            t    = (st["std"] / diff) if diff > st["std"] else 1.0
            transformed.append(t)
            t_dict[col] = round(float(t), 4)

        X    = np.array([transformed])
        pred = self.xgb.predict(X)[0]
        prob = self.xgb.predict_proba(X)[0]
        cmap = {0: "정상", 1: "경증", 2: "중증"}

        return {
            "severity_class": int(pred),
            "severity_label": cmap[int(pred)],
            "probs": {
                "정상": round(float(prob[0]), 4),
                "경증": round(float(prob[1]), 4),
                "중증": round(float(prob[2]), 4),
            },
            "metrics": {
                "prr": round(prr, 2),
                "crr": round(crr, 2),
                "vrr": round(vrr, 2),
            },
        }


# ── 엔진 로더 ────────────────────────────────────────────────
def get_putterker_engine():
    global _putterker_engine
    if _putterker_engine is None:
        _putterker_engine = PutterkerEngine()
    return _putterker_engine

def get_aiiu_engine():
    global _aiiu_engine
    if _aiiu_engine is None:
        _aiiu_engine = AiiuEngine()
    return _aiiu_engine

def get_word_engine():
    global _word_engine
    if _word_engine is None:
        _word_engine = WordEngine()
    return _word_engine


# ── 오디오 변환 헬퍼 ─────────────────────────────────────────
def save_as_wav(upload_file_content: bytes, tmp_dir: str, name: str) -> str:
    """업로드된 바이트를 wav로 변환 후 임시 경로 반환"""
    raw_path = os.path.join(tmp_dir, f"{name}_raw")
    wav_path = os.path.join(tmp_dir, f"{name}.wav")
    with open(raw_path, "wb") as f:
        f.write(upload_file_content)
    y, sr = librosa.load(raw_path, sr=16000, mono=True)
    sf.write(wav_path, y, sr)
    return wav_path


# ── 엔드포인트 ───────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    try:
        get_putterker_engine()
        print("[서버] 퍼터커 엔진 로드 완료")
    except Exception as e:
        print(f"[경고] 퍼터커 엔진 로드 실패: {e}")
    try:
        get_aiiu_engine()
        print("[서버] 아이우 엔진 로드 완료")
    except Exception as e:
        print(f"[경고] 아이우 엔진 로드 실패: {e}")
    try:
        get_word_engine()
        print("[서버] 단어 엔진 로드 완료")
    except Exception as e:
        print(f"[경고] 단어 엔진 로드 실패: {e}")
    print("[서버] 모든 모델 준비 완료!")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "putterker_loaded": _putterker_engine is not None,
        "aiiu_loaded":     _aiiu_engine is not None,
        "word_loaded":     _word_engine is not None,
    }


@app.post("/api/predict_word")
async def predict_word(
    sex:   str            = Form(...),
    age:   int            = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    단어 발화 wav 파일들(여러 개)을 받아 XGBoost+Wav2Vec2로 중증도 추론.
    - sex  : 'M' 또는 'F'
    - age  : 나이 (int)
    - files: 단어 녹음 wav 파일 목록 (파일명에 단어 포함 필요)
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        wav_paths = []
        for f in files:
            content  = await f.read()
            raw_path = os.path.join(tmp_dir, f.filename)
            with open(raw_path, "wb") as fp:
                fp.write(content)
            wav_path = os.path.join(tmp_dir,
                                    os.path.splitext(f.filename)[0] + ".wav")
            y, sr = librosa.load(raw_path, sr=16000, mono=True)
            sf.write(wav_path, y, sr)
            wav_paths.append(wav_path)

        if not wav_paths:
            raise HTTPException(status_code=400, detail="단어 음성 파일이 없습니다.")

        eng    = get_word_engine()
        result = eng.predict(wav_paths, sex, age)
        return {"status": "success", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"단어 추론 오류: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/predict")
async def predict(
    putterker: Optional[UploadFile]       = File(None),
    vowel_a:   Optional[UploadFile]       = File(None),
    vowel_i:   Optional[UploadFile]       = File(None),
    vowel_u:   Optional[UploadFile]       = File(None),
    word_files: Optional[List[UploadFile]] = File(None),
    word_sex:  Optional[str]              = Form(None),
    word_age:  Optional[int]              = Form(None),
    # 하위 호환 필드
    vowel:     Optional[UploadFile]       = File(None),
):
    """
    음성 파일을 받아 세 모델로 추론 후 종합 결과 반환.
    - putterker        : 퍼터커 발성 (ResNet+Fusion+MLP)
    - vowel_a/i/u      : 아/이/우 모음 (15D Cascade-SVM)
    - word_files+sex/age: 단어 발화 (XGBoost+Wav2Vec2)
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        result_putterker = None
        result_aiiu      = None
        result_word      = None

        # ── 퍼터커 추론 ──────────────────────────────────────
        if putterker is not None:
            content  = await putterker.read()
            wav_path = save_as_wav(content, tmp_dir, "putterker")
            eng      = get_putterker_engine()
            result_putterker = eng.predict(wav_path)

        # ── 아이우 추론 ──────────────────────────────────────
        if vowel_a is not None and vowel_i is not None and vowel_u is not None:
            content_a = await vowel_a.read()
            content_i = await vowel_i.read()
            content_u = await vowel_u.read()
            path_a = save_as_wav(content_a, tmp_dir, "vowel_a")
            path_i = save_as_wav(content_i, tmp_dir, "vowel_i")
            path_u = save_as_wav(content_u, tmp_dir, "vowel_u")
            result_aiiu = get_aiiu_engine().predict(path_a, path_i, path_u)

        # ── 단어 추론 ────────────────────────────────────────
        if word_files:
            wav_paths = []
            for f in word_files:
                content  = await f.read()
                raw_path = os.path.join(tmp_dir, f"word_{f.filename}")
                with open(raw_path, "wb") as fp:
                    fp.write(content)
                wav_path = os.path.join(tmp_dir,
                                        "word_" + os.path.splitext(f.filename)[0] + ".wav")
                y, sr = librosa.load(raw_path, sr=16000, mono=True)
                sf.write(wav_path, y, sr)
                wav_paths.append(wav_path)
            sex = word_sex or "M"
            age = word_age or 50
            result_word = get_word_engine().predict(wav_paths, sex, age)

        # ── 종합 중증도 계산 (모든 제출 모델 중 최대) ────────
        scores = []
        if result_putterker:
            scores.append(result_putterker["severity_class"])
        if result_aiiu:
            scores.append(result_aiiu["severity_class"])
        if result_word:
            scores.append(result_word["severity_class"])

        if not scores:
            raise HTTPException(status_code=400, detail="분석할 음성 파일이 없습니다.")

        final_class = max(scores)
        label_map   = {0: "정상", 1: "경증", 2: "중증"}
        score_map   = {0: 0, 1: 3, 2: 6}

        return {
            "status":         "success",
            "severity_label": label_map[final_class],
            "severity_class": final_class,
            "total_score":    score_map[final_class],
            "details": {
                "putterker": result_putterker,
                "vowel":     result_aiiu,
                "word":      result_word,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추론 오류: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

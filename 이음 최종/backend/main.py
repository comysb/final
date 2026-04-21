"""

留먭만 FastAPI 諛깆뿏뱶 v3

- 띁꽣而(DDK)  : ResNet+Fusion+MLP 留덉뒪꽣 紐⑤뜽

- 紐⑥쓬(븘/씠/슦): 15D Cascade-SVM 留덉뒪꽣 紐⑤뜽

- 떒뼱         : XGBoost + Wav2Vec2 쓬냼 젙젹 紐⑤뜽

"""

import os

import sys

import glob

import json

import pickle

import tempfile

import shutil

import uuid

import importlib.util

import numpy as np

import torch

import librosa

import soundfile as sf

import joblib

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, WebSocket, WebSocketDisconnect

from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware

from typing import Optional, List

import warnings

warnings.filterwarnings("ignore")

import noisereduce as nr

from scoring import build_full_report

from rehab_pipeline import RehabSessionProcessor

from rehab_evaluator import EvaluatorConfig

from realtime_stream import stream_manager

import baseline_estimator



#  씤肄붾뵫 꽕젙 (Windows cp949 쓳) 

import sys

import io

if sys.stdout.encoding != 'utf-8':

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

if sys.stderr.encoding != 'utf-8':

    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')



#  寃쎈줈 꽕젙 

PUTTERKER_DIR = r"D:\퍼터커"

AIIU_DIR      = r"D:\아이우"

WORD_DIR      = r"D:\단어"

MODEL_DIR     = os.path.join(PUTTERKER_DIR, "models", "master")

WORD_MODEL_DIR = os.path.join(WORD_DIR, "models")

DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"



#  紐⑤뱢 룞쟻 엫룷듃 뿬띁 

def _load_module(name, filepath):

    spec = importlib.util.spec_from_file_location(name, filepath)

    mod = importlib.util.module_from_spec(spec)

    sys.modules[name] = mod

    spec.loader.exec_module(mod)

    return mod



#  빋 깮꽦 

app = FastAPI(title="留먭만 API v2", version="2.0.0")



app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



#  쟾뿭 뿏吏 떛湲꽩 

_putterker_engine = None

_aiiu_engine      = None

_word_engine      = None



# 

# 1. 띁꽣而 뿏吏 (ResNet + Fusion + MLP)

# 

class PutterkerEngine:

    def __init__(self):

        print("[띁꽣而] 紐⑤뱢 濡쒕뱶 以...")

        if PUTTERKER_DIR not in sys.path:

            sys.path.insert(0, PUTTERKER_DIR)



        self.m_enc  = _load_module("m_enc",  os.path.join(PUTTERKER_DIR, "03_deep_encoders.py"))

        self.m_fus  = _load_module("m_fus",  os.path.join(PUTTERKER_DIR, "04_attention_fusion.py"))

        self.m_cls  = _load_module("m_cls",  os.path.join(PUTTERKER_DIR, "05-1_train_classifier.py"))

        self.m_feat = _load_module("m_feat", os.path.join(PUTTERKER_DIR, "02_feature_extraction.py"))



        print("[띁꽣而] 뒪耳씪윭 & 엫怨꾧컪 濡쒕뱶 以...")

        with open(os.path.join(MODEL_DIR, "scaler_master.pkl"), "rb") as f:

            self.scaler = pickle.load(f)

        with open(os.path.join(MODEL_DIR, "thresholds.json"), "r", encoding="utf-8") as f:

            self.thresholds = json.load(f)



        print("[띁꽣而] PyTorch 紐⑤뜽 濡쒕뱶 以...")

        self.resnet     = self.m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)

        self.fusion     = self.m_fus.FeatureFusion(ddk_dim=12, w2v_dim=256, mel_dim=256, fusion_dim=256).to(DEVICE)

        self.classifier = self.m_cls.DysarthriaMLPClassifier(input_dim=self.fusion.total_dim, num_classes=3).to(DEVICE)



        self.resnet.load_state_dict(torch.load(os.path.join(MODEL_DIR, "resnet_master.pt"), map_location=DEVICE))

        self.fusion.load_state_dict(torch.load(os.path.join(MODEL_DIR, "fusion_master.pt"), map_location=DEVICE))

        self.classifier.load_state_dict(torch.load(os.path.join(MODEL_DIR, "classifier_master.pt"), map_location=DEVICE))

        self.resnet.eval(); self.fusion.eval(); self.classifier.eval()



        print("[띁꽣而] LSTM 쓬젅遺꾪븷湲 濡쒕뱶 以...")

        self.lstm_model = self.m_feat.get_lstm_model(device=DEVICE)

        print("[띁꽣而] 뿏吏 以鍮 셿猷!")



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



        label_map = {0: "젙긽", 1: "寃쎌쬆", 2: "以묒쬆"}

        return {

            "severity_class": severity_class,

            "severity_label": label_map[severity_class],

            "probs": {

                "젙긽": round(float(probs[0]), 4),

                "寃쎌쬆": round(float(probs[1]), 4),

                "以묒쬆": round(float(probs[2]), 4),

            },

            "features": {k: round(float(v), 4) for k, v in ddk_feats.items()},

        }





# 

# 2. 븘씠슦 뿏吏 (15D Cascade-SVM)

# 

class AiiuEngine:

    def __init__(self):

        print("[븘씠슦] 15D Cascade-SVM 뿏吏 濡쒕뱶 以...")

        # 븘씠슦 pipeline 뙣궎吏瑜 sys.path뿉 異붽

        if AIIU_DIR not in sys.path:

            sys.path.insert(0, AIIU_DIR)



        from pipeline.inference_engine import DysarthriaInferenceEngine

        self.engine = DysarthriaInferenceEngine()

        print("[븘씠슦] 뿏吏 以鍮 셿猷!")



    def predict(self, path_a: str, path_i: str, path_u: str) -> dict:

        result = self.engine.predict(path_a, path_i, path_u)

        severity_class = result.get("recommended_result", 0)

        label_map = {0: "젙긽", 1: "寃쎌쬆", 2: "以묒쬆"}

        probs = result.get("class_probabilities", {"젙긽": 0.0, "寃쎌쬆": 0.0, "以묒쬆": 0.0})



        # raw Praat 뵾泥 異붿텧 (쁺뿭 젏닔 怨꾩궛슜)

        raw_feats = {}

        try:

            feat_data = self.engine.extract_features(path_a, path_i, path_u)

            import numpy as _np

            if isinstance(feat_data, dict):
                raw_feats = {k: round(float(v), 5) for k, v in feat_data.items()
                             if k not in ("UID", "speaker_id") and v is not None and str(v) != "nan"}

            elif isinstance(feat_data, _np.ndarray):
                # extract_features는 ndarray(1x112)를 반환함 → feat_cols로 dict 변환
                arr = feat_data.flatten()
                cols = self.engine.feat_cols if hasattr(self.engine, 'feat_cols') else []
                for _i, _col in enumerate(cols):
                    if _i < len(arr):
                        _v = float(arr[_i])
                        if _v == _v and _col not in ('UID', 'speaker_id'):
                            raw_feats[_col] = round(_v, 5)

            print(f'[아이우] raw 피처 {len(raw_feats)}개 추출 완료')

        except Exception as e:

            print(f"[아이우] raw 피처 추출 실패: {e}")



        # 븘씠슦 뿏吏꾩 % 떒쐞濡 諛섑솚 넂 0~1濡 젙洹쒗솕

        return {

            "severity_class": severity_class,

            "severity_label": label_map.get(severity_class, "젙긽"),

            "probs": {

                "젙긽": round(probs.get("젙긽", 0) / 100, 4),

                "寃쎌쬆": round(probs.get("寃쎌쬆", 0) / 100, 4),

                "以묒쬆": round(probs.get("以묒쬆", 0) / 100, 4),

            },

            "features": raw_feats,

        }





# 

# 3. 떒뼱 뿏吏 (XGBoost + Wav2Vec2 쓬냼 젙젹)

# 

class WordEngine:

    """

    D:\떒뼱 쓽 XGBoost(final_xgb_model.json) + Wav2Vec2 쓬냼 젙젹 湲곕컲

    떒뼱 諛쒗솕 以묒쬆룄 遺꾨쪟 뿏吏.

    엯젰 : 떒뼱 wav 뙆씪 紐⑸줉 + sex(M/F) + age(int)

    異쒕젰 : severity_class(0/1/2), severity_label, probs, metrics

    """

    FEATURE_COLS = [

        "jitter", "shimmer", "apq",

        "crr", "vrr", "prr",

        "mean_f0", "median_f0", "min_f0", "max_f0",

        "mean_energy", "median_energy", "std_energy", "min_energy", "max_energy",

        "vsa_triangle", "fcr", "vai", "f2_ratio",

    ]



    def __init__(self):

        print("[떒뼱] 紐⑤뜽 濡쒕뱶 以...")

        if WORD_DIR not in sys.path:

            sys.path.insert(0, WORD_DIR)



        # acoustic_utils 룞쟻 엫룷듃

        self.utils = _load_module("word_acoustic_utils",

                                  os.path.join(WORD_DIR, "acoustic_utils.py"))



        # XGBoost 紐⑤뜽

        from xgboost import XGBClassifier

        self.xgb = XGBClassifier()

        self.xgb.load_model(os.path.join(WORD_MODEL_DIR, "final_xgb_model.json"))



        # 젙洹쒗솕 넻怨

        self.healthy_stats = joblib.load(os.path.join(WORD_MODEL_DIR, "healthy_stats.joblib"))

        self.pitch_stats   = joblib.load(os.path.join(WORD_MODEL_DIR, "pitch_stats.joblib"))



        # Wav2Vec2 (쓬냼 젙젹슜)

        print("[떒뼱] Wav2Vec2 濡쒕뱶 以 (떆媛 냼슂)...")

        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        w2v_path = os.path.join(WORD_MODEL_DIR, "wav2vec2_acoustic")

        self.processor = Wav2Vec2Processor.from_pretrained(w2v_path)

        self.w2v_model = Wav2Vec2ForCTC.from_pretrained(w2v_path).to(DEVICE).eval()

        self.vocab = self.processor.tokenizer.get_vocab()



        # MFA 궗쟾 & 젙以 쓬냼뿴

        u = self.utils

        self.mfa_dict = u.load_mfa_dictionary(u.MFA_DICT_PATH)

        self.can_all, self.can_cons, self.can_vows = \
            u.build_canonical_sequence(u.DEFAULT_WORDS, self.mfa_dict)

        self.word_order = {w: i for i, w in enumerate(u.DEFAULT_WORDS)}

        print("[떒뼱] 뿏吏 以鍮 셿猷!")



    def predict(self, wav_paths: list, sex: str, age: int) -> dict:

        """wav 뙆씪 寃쎈줈 由ъ뒪듃 넂 떒뼱 紐⑤뜽 異붾줎 寃곌낵 諛섑솚"""

        u = self.utils

        sex_key = str(sex).strip().upper()

        max_f   = 5000.0 if sex_key in ["M", "궓", "MALE", "1"] else 5500.0



        # 뙆씪쓣 떒뼱 닚꽌濡 젙젹

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

        cmap = {0: "젙긽", 1: "寃쎌쬆", 2: "以묒쬆"}



        return {

            "severity_class": int(pred),

            "severity_label": cmap[int(pred)],

            "probs": {

                "젙긽": round(float(prob[0]), 4),

                "寃쎌쬆": round(float(prob[1]), 4),

                "以묒쬆": round(float(prob[2]), 4),

            },

            "metrics": {

                "prr": round(prr, 2),

                "crr": round(crr, 2),

                "vrr": round(vrr, 2),

            },

        }





#  뿏吏 濡쒕뜑 

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





#  삤뵒삤 蹂솚 뿬띁 

def save_as_wav(upload_file_content: bytes, tmp_dir: str, name: str, y_noise=None) -> str:

    """뾽濡쒕뱶맂 諛붿씠듃瑜 wav濡 蹂솚 썑 엫떆 寃쎈줈 諛섑솚"""

    raw_path = os.path.join(tmp_dir, f"{name}_raw")

    wav_path = os.path.join(tmp_dir, f"{name}.wav")

    with open(raw_path, "wb") as f:

        f.write(upload_file_content)

    

    # 뵒踰꾧퉭: 썝蹂 뙆씪 겕湲 濡쒓퉭

    raw_size = len(upload_file_content)

    

    try:

        y, sr = librosa.load(raw_path, sr=16000, mono=True)

        if y_noise is not None and len(y) > 0:

            y = nr.reduce_noise(y=y, sr=sr, y_noise=y_noise)

            print(f"[{name}] 끂씠利 罹붿뒳留 쟻슜 셿猷")

            

        dur = len(y) / sr

        rms = np.sqrt(np.mean(y**2)) if len(y) > 0 else 0

        print(f"[삤뵒삤 濡쒓렇] {name}: {raw_size} bytes -> {dur:.2f}s (RMS: {rms:.4f})")

        sf.write(wav_path, y, sr)

    except Exception as e:

        print(f"[삤뵒삤 뿉윭] {name} 蹂솚 떎뙣: {e}")

        # 鍮 뙆씪씠씪룄 깮꽦븯뿬 뿉윭 諛⑹

        sf.write(wav_path, np.zeros(1600), 16000)

        

    return wav_path





#  뿏뱶룷씤듃 



@app.on_event("startup")

async def startup_event():

    try:

        get_putterker_engine()

        print("[꽌踰] 띁꽣而 뿏吏 濡쒕뱶 셿猷")

    except Exception as e:

        print(f"[寃쎄퀬] 띁꽣而 뿏吏 濡쒕뱶 떎뙣: {e}")

    try:

        get_aiiu_engine()

        print("[꽌踰] 븘씠슦 뿏吏 濡쒕뱶 셿猷")

    except Exception as e:

        print(f"[寃쎄퀬] 븘씠슦 뿏吏 濡쒕뱶 떎뙣: {e}")

    try:

        get_word_engine()

        print("[꽌踰] 떒뼱 뿏吏 濡쒕뱶 셿猷")

    except Exception as e:

        print(f"[寃쎄퀬] 떒뼱 뿏吏 濡쒕뱶 떎뙣: {e}")

    print("[꽌踰] 紐⑤뱺 紐⑤뜽 以鍮 셿猷!")





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

    떒뼱 諛쒗솕 wav 뙆씪뱾(뿬윭 媛)쓣 諛쏆븘 XGBoost+Wav2Vec2濡 以묒쬆룄 異붾줎.

    - sex  : 'M' 삉뒗 'F'

    - age  : 굹씠 (int)

    - files: 떒뼱 끃쓬 wav 뙆씪 紐⑸줉 (뙆씪紐낆뿉 떒뼱 룷븿 븘슂)

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

            raise HTTPException(status_code=400, detail="떒뼱 쓬꽦 뙆씪씠 뾾뒿땲떎.")



        eng    = get_word_engine()

        result = eng.predict(wav_paths, sex, age)

        return {"status": "success", "data": result}



    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(status_code=500, detail=f"떒뼱 異붾줎 삤瑜: {str(e)}")

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

    noise_file: Optional[UploadFile]      = File(None),

    # 븯쐞 샇솚 븘뱶

    vowel:     Optional[UploadFile]       = File(None),

):

    """

    쓬꽦 뙆씪쓣 諛쏆븘 꽭 紐⑤뜽濡 異붾줎 썑 醫낇빀 寃곌낵 諛섑솚.

    - putterker        : 띁꽣而 諛쒖꽦 (ResNet+Fusion+MLP)

    - vowel_a/i/u      : 븘/씠/슦 紐⑥쓬 (15D Cascade-SVM)

    - word_files+sex/age: 떒뼱 諛쒗솕 (XGBoost+Wav2Vec2)

    - noise_file       : 솚寃 냼쓬 뙆씪 (쟻쓳삎 끂씠利 罹붿뒳留곸슜)

    """

    tmp_dir = tempfile.mkdtemp()

    try:

        result_putterker = None

        result_aiiu      = None

        result_word      = None



        #  諛곌꼍 냼쓬 봽濡쒗븘 遺꾩꽍 

        y_noise = None

        if noise_file is not None:

            try:

                noise_content = await noise_file.read()

                raw_noise_path = os.path.join(tmp_dir, "noise_raw")

                with open(raw_noise_path, "wb") as f:

                    f.write(noise_content)

                y_noise, _ = librosa.load(raw_noise_path, sr=16000, mono=True)

                print(f"[삤뵒삤 濡쒓렇] 二쇰 냼쓬 봽濡쒗븘 솗蹂 ({len(y_noise)/16000:.2f}s)")

            except Exception as e:

                print(f"[삤뵒삤 寃쎄퀬] 냼쓬 뙆씪 濡쒕뱶 떎뙣: {e}")



        #  띁꽣而 異붾줎 

        if putterker is not None:

            content  = await putterker.read()

            # 띁꽣而(뙆뿴쓬)뒗 끂씠利 罹붿뒳留곸쓣 쟻슜븯硫 뙆뿴쓬씠 넀긽맆 닔 엳쑝誘濡 y_noise 쟻슜 븞 븿

            wav_path = save_as_wav(content, tmp_dir, "putterker")

            try:

                eng      = get_putterker_engine()

                result_putterker = eng.predict(wav_path)

            except Exception as e:

                import traceback

                print(f"[Putterker Error] {e}")

                traceback.print_exc()

                result_putterker = {"severity_class": 2, "probs": {"젙긽":0, "寃쎌쬆":0, "以묒쬆":1}}



        #  븘씠슦 異붾줎 

        if vowel_a is not None and vowel_i is not None and vowel_u is not None:

            content_a = await vowel_a.read()

            content_i = await vowel_i.read()

            content_u = await vowel_u.read()

            path_a = save_as_wav(content_a, tmp_dir, "vowel_a", y_noise=y_noise)

            path_i = save_as_wav(content_i, tmp_dir, "vowel_i", y_noise=y_noise)

            path_u = save_as_wav(content_u, tmp_dir, "vowel_u", y_noise=y_noise)

            try:

                result_aiiu = get_aiiu_engine().predict(path_a, path_i, path_u)

            except Exception as e:

                import traceback

                print(f"[Aiiu Error] {e}")

                traceback.print_exc()

                result_aiiu = {"severity_class": 2, "probs": {"젙긽":0, "寃쎌쬆":0, "以묒쬆":1}}



        #  떒뼱 異붾줎 

        if word_files:

            wav_paths = []

            for f in word_files:

                content  = await f.read()

                raw_path = os.path.join(tmp_dir, f"word_{f.filename}")

                with open(raw_path, "wb") as fp:

                    fp.write(content)

                wav_path = os.path.join(tmp_dir,

                                        "word_" + os.path.splitext(f.filename)[0] + ".wav")

                try:

                    y, sr = librosa.load(raw_path, sr=16000, mono=True)

                    if y_noise is not None and len(y) > 0:

                        y = nr.reduce_noise(y=y, sr=sr, y_noise=y_noise)

                    sf.write(wav_path, y, sr)

                    wav_paths.append(wav_path)

                except Exception:

                    pass

            sex = word_sex or "M"

            age = word_age or 50

            try:

                result_word = get_word_engine().predict(wav_paths, sex, age)

                # 뵒踰꾧퉭: Word 뿏吏 寃곌낵 濡쒓퉭

                if result_word:

                    m = result_word.get("metrics", {})

                    print(f"[Word 濡쒓렇] PRR: {m.get('prr')}, CRR: {m.get('crr')}, VRR: {m.get('vrr')}")

            except Exception as e:

                import traceback

                print(f"[Word Error] {e}")

                traceback.print_exc()

                result_word = {"severity_class": 2, "probs": {"젙긽":0, "寃쎌쬆":0, "以묒쬆":1}, "error": str(e)}



        #  醫낇빀 以묒쬆룄 怨꾩궛 (紐⑤뱺 젣異 紐⑤뜽 以 理쒕) 

        scores = []

        if result_putterker:

            scores.append(result_putterker["severity_class"])

        if result_aiiu:

            scores.append(result_aiiu["severity_class"])

        if result_word:

            scores.append(result_word["severity_class"])



        import json

        with open("last_predict_trace.json", "w", encoding="utf-8") as f:

            json.dump({

                "putterker": result_putterker,

                "aiiu": result_aiiu,

                "word": result_word,

                "scores": scores

            }, f, indent=2, ensure_ascii=False)



        if not scores:

            raise HTTPException(status_code=400, detail="遺꾩꽍븷 쓬꽦 뙆씪씠 뾾뒿땲떎.")



        # 醫낇빀 以묒쬆룄뒗 3媛 紐⑤뜽쓽 룊洹좎쓣 諛섏삱由쇳븯뿬 궗슜 (떎 以묒쬆쑝濡 굹삤뒗 寃 諛⑹)

        final_class = int(round(sum(scores) / len(scores)))

        label_map   = {0: "젙긽", 1: "寃쎌쬆", 2: "以묒쬆"}

        score_map   = {0: 0, 1: 3, 2: 6}



        #  4媛 쁺뿭 젏닔 怨꾩궛 

        try:

            pk_feats  = result_putterker.get("features", {}) if result_putterker else {}

            ai_feats  = result_aiiu.get("features", {})      if result_aiiu      else {}

            wd_feats  = result_word.get("raw_features", {})  if result_word      else {}

            # 떒뼱 metrics(CRR/VRR/PRR)룄 룷븿

            if result_word and "metrics" in result_word:

                wd_feats.update(result_word["metrics"])

            domain_report = build_full_report(pk_feats, ai_feats, wd_feats)

        except Exception as e:

            print(f"[Scoring] 쁺뿭 젏닔 怨꾩궛 떎뙣: {e}")

            domain_report = {"domain_scores": {}, "overall_score": None}



        return {

            "status":         "success",

            "severity_label": label_map[final_class],

            "severity_class": final_class,

            "total_score":    score_map[final_class],

            "domain_scores":  domain_report.get("domain_scores", {}),

            "overall_score":  domain_report.get("overall_score"),

            "overall_level":  domain_report.get("overall_level"),

            "details": {

                "putterker": result_putterker,

                "vowel":     result_aiiu,

                "word":      result_word,

            },

        }



    except HTTPException:

        raise

    except Exception as e:

        import traceback

        tb_str = traceback.format_exc()

        print(tb_str)

        raise HTTPException(status_code=500, detail=f"異붾줎 삤瑜: {str(e)}\nTraceback: {tb_str}")

    finally:

        shutil.rmtree(tmp_dir, ignore_errors=True)





# =====================================================================

# 옱솢썕젴 룊媛 API  (/api/rehab/*)   8080 넻빀

# =====================================================================

CHUNK_SR   = 16000

_rehab_processor = RehabSessionProcessor(config=EvaluatorConfig())





async def _save_rehab_upload(file: UploadFile, tmp_dir: str) -> str:

    p = os.path.join(tmp_dir, file.filename)

    content = await file.read()

    with open(p, "wb") as f:

        f.write(content)

    if not file.filename.endswith(".wav"):

        wav_p = os.path.splitext(p)[0] + ".wav"

        y, sr = librosa.load(p, sr=16000)

        sf.write(wav_p, y, sr)

        return wav_p

    return p





async def _run_rehab_eval(file: UploadFile, process_fn):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = process_fn(wav_path)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/calibrate")

async def rehab_calibrate(file: UploadFile = File(...)):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        _rehab_processor.set_session_baseline(wav_path)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "ok", "message": "踰좎씠뒪씪씤 罹섎━釉뚮젅씠뀡 셿猷"})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/breathing")

async def rehab_breathing(file: UploadFile = File(...)):

    return await _run_rehab_eval(file, _rehab_processor.process_breathing_proxy)





@app.post("/api/rehab/sustained_phonation")

async def rehab_sustained_phonation(file: UploadFile = File(...), target_duration: Optional[float] = Form(default=None)):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = _rehab_processor.process_sustained_phonation(wav_path, target_duration=target_duration)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/pitch_glide")

async def rehab_pitch_glide(file: UploadFile = File(...), direction: str = Form(default="up"), target_change_percent: Optional[float] = Form(default=None)):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = _rehab_processor.process_pitch_glide(wav_path, direction=direction, target_change_percent=target_change_percent)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/pitch_control")

async def rehab_pitch_control(file: UploadFile = File(...), target_ratio: Optional[float] = Form(default=1.10), hz_tolerance: Optional[float] = Form(default=5.0)):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = _rehab_processor.process_pitch_control(wav_path, target_ratio=target_ratio, hz_tolerance=hz_tolerance)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/loudness_control")

async def rehab_loudness_control(file: UploadFile = File(...), target_gain_db: float = Form(default=6.0)):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = _rehab_processor.process_loudness_control(wav_path, target_gain_db=target_gain_db)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/glottal_closure")

async def rehab_glottal_closure(file: UploadFile = File(...)):

    return await _run_rehab_eval(file, _rehab_processor.process_glottal_closure)





@app.post("/api/rehab/ddk")

async def rehab_ddk(

    file: UploadFile = File(...),

    target_sequence: Optional[str] = Form(default=None),

    predicted_sequence: Optional[str] = Form(default=None),

    target_rate: Optional[float] = Form(default=None),

):

    import json as _json

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        tgt = _json.loads(target_sequence)    if target_sequence    else None

        prd = _json.loads(predicted_sequence) if predicted_sequence else None

        result = _rehab_processor.process_ddk(wav_path, target_rate=target_rate, target_sequence=tgt, predicted_sequence=prd)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/slow_reading")

async def rehab_slow_reading(

    file: UploadFile = File(...),

    prompt_text: str = Form(...),

    pause_duration: float = Form(default=0.0),

    target_time_min: Optional[float] = Form(default=None),

    target_time_max: Optional[float] = Form(default=None),

):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = _rehab_processor.process_slow_reading(wav_path, prompt_text=prompt_text, pause_duration=pause_duration, target_time_min=target_time_min, target_time_max=target_time_max)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





@app.post("/api/rehab/loud_reading")

async def rehab_loud_reading(

    file: UploadFile = File(...),

    prompt_text: str = Form(...),

    normal_reading_loudness: Optional[float] = Form(default=None),

    target_gain_db: Optional[float] = Form(default=None),

):

    tmp = f"temp_audio/{uuid.uuid4()}"

    try:

        os.makedirs(tmp, exist_ok=True)

        wav_path = await _save_rehab_upload(file, tmp)

        result   = _rehab_processor.process_loud_reading(wav_path, prompt_text=prompt_text, normal_reading_loudness=normal_reading_loudness, target_gain_db=target_gain_db)

        from fastapi.responses import JSONResponse

        return JSONResponse(content={"status": "success", "data": result})

    except Exception as e:

        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"error": str(e)})

    finally:

        shutil.rmtree(tmp, ignore_errors=True)





# =====================================================================

# WebSocket: 떎떆媛 뒪듃由щ컢 룊媛  ws://localhost:8080/ws/rehab/live

# =====================================================================

@app.websocket("/ws/rehab/live")

async def ws_rehab_live(websocket: WebSocket):

    await websocket.accept()

    session_id: Optional[str] = None

    calibrating: bool = False



    try:

        while True:

            msg = await websocket.receive()



            if "bytes" in msg and msg["bytes"] is not None:

                raw_bytes = msg["bytes"]

                pcm_int16 = np.frombuffer(raw_bytes, dtype=np.int16)



                if calibrating:

                    pcm_f32  = pcm_int16.astype(np.float32) / 32768.0

                    baseline = baseline_estimator.extract_baseline_features_from_array(pcm_f32)

                    if session_id and session_id in stream_manager._sessions:

                        stream_manager._sessions[session_id].baseline = baseline

                    _rehab_processor.baseline = baseline

                    calibrating = False

                    from fastapi.responses import JSONResponse

                    await websocket.send_text(

                        json.dumps({"type": "calibrated", "baseline": {

                            k: v for k, v in baseline.items()

                            if isinstance(v, (int, float, str, bool))

                        }})

                    )

                else:

                    if session_id:

                        stream_manager.push(session_id, pcm_int16)

                        feedback = stream_manager.feedback(session_id)

                        await websocket.send_text(json.dumps({"type": "live", "data": feedback}))

                continue



            if "text" not in msg or msg["text"] is None:

                continue



            ctrl     = json.loads(msg["text"])

            msg_type = ctrl.get("type")



            if msg_type == "open":

                session_id = ctrl.get("session_id") or str(uuid.uuid4())

                task_type  = ctrl.get("task_type", "sustained_phonation")

                baseline   = _rehab_processor.baseline or {

                    "success": True, "quality_flag": "ok",

                    "baseline_f0": 150.0, "baseline_loudness": -30.0,

                    "noise_floor": -60.0, "voiced_ratio": 0.0, "source": "default"

                }

                stream_manager.open(session_id, task_type, baseline)

                await websocket.send_text(json.dumps({"type": "opened", "session_id": session_id}))



            elif msg_type == "calibrate":

                calibrating = True



            elif msg_type == "close":

                full_audio = stream_manager.close(session_id)

                if full_audio is not None and len(full_audio) > 0:

                    tmp_f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

                    sf.write(tmp_f.name, full_audio, CHUNK_SR)

                    tmp_f.close()

                    task_type = ctrl.get("task_type", "sustained_phonation")

                    result = _rehab_route_final(tmp_f.name, task_type, ctrl)

                    os.unlink(tmp_f.name)

                    await websocket.send_text(json.dumps({"type": "final", "data": result}))

                break



    except WebSocketDisconnect:

        if session_id:

            stream_manager.close(session_id)

    except Exception as e:

        if session_id:

            stream_manager.close(session_id)

        try:

            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))

        except Exception:

            pass





def _rehab_route_final(wav_path: str, task_type: str, extra: dict) -> dict:

    routing = {

        "breathing":           _rehab_processor.process_breathing_proxy,

        "sustained_phonation": lambda p: _rehab_processor.process_sustained_phonation(p, target_duration=extra.get("target_duration")),

        "pitch_glide_up":      lambda p: _rehab_processor.process_pitch_glide(p, direction="up",   target_change_percent=extra.get("target_change_percent")),

        "pitch_glide_down":    lambda p: _rehab_processor.process_pitch_glide(p, direction="down", target_change_percent=extra.get("target_change_percent")),

        "pitch_control":       lambda p: _rehab_processor.process_pitch_control(p, target_ratio=extra.get("target_ratio"), hz_tolerance=extra.get("hz_tolerance", 5.0)),

        "loudness_control":    lambda p: _rehab_processor.process_loudness_control(p, target_gain_db=extra.get("target_gain_db")),

        "glottal_closure":     _rehab_processor.process_glottal_closure,

        "ddk":                 lambda p: _rehab_processor.process_ddk(p, target_rate=extra.get("target_rate")),

        "slow_reading":        lambda p: _rehab_processor.process_slow_reading(p, prompt_text=extra.get("prompt_text", ""), pause_duration=extra.get("pause_duration", 0.0), target_time_min=extra.get("target_time_min"), target_time_max=extra.get("target_time_max")),

        "loud_reading":        lambda p: _rehab_processor.process_loud_reading(p, prompt_text=extra.get("prompt_text", ""), normal_reading_loudness=extra.get("normal_reading_loudness"), target_gain_db=extra.get("target_gain_db")),

    }

    fn = routing.get(task_type)

    if fn:

        try:

            return fn(wav_path)

        except Exception as e:

            return {"status": "error", "message": str(e)}

    return {"status": "dummy", "task_type": task_type}

# app.mount("/", StaticFiles(directory="D:/이음최종/prototype", html=True), name="prototype")  # 주석처리: 아래 명시적 라우트가 우선 처리







# == Static File Serving (prototype directory) ==

from fastapi.staticfiles import StaticFiles

from fastapi.responses import FileResponse



PROTOTYPE_DIR = r'D:\이음최종\prototype'



@app.get('/chunk_processor.js')

def serve_chunk_js():

    p = os.path.join(PROTOTYPE_DIR, 'chunk_processor.js')

    if os.path.exists(p):

        return FileResponse(p, media_type='application/javascript')

    return FileResponse(os.path.join(r'D:\이음', 'chunk_processor.js'), media_type='application/javascript')



@app.get('/therapy_ui_v4.html')

def serve_frontend():

    return FileResponse(os.path.join(PROTOTYPE_DIR, 'therapy_ui_v4.html'), media_type='text/html')



@app.get('/')

def serve_root():

    return FileResponse(os.path.join(PROTOTYPE_DIR, 'therapy_ui_v4.html'), media_type='text/html')



# ── 마음이음 라우터를 StaticFiles('/') 보다 먼저 등록 (순서 중요!)
try:
    from maeum_router import router as maeum_router, SVC_DIR as _SVC_DIR
    from fastapi.staticfiles import StaticFiles as _MaeumSS
    app.include_router(maeum_router)
    if _SVC_DIR.is_dir():
        app.mount("/maeum/assets", _MaeumSS(directory=str(_SVC_DIR)), name="maeum-static")
    print("[마음이음] 라우터 등록 완료 — http://localhost:8080/maeum/")
except Exception as _e:
    print(f"[마음이음] 라우터 등록 실패: {_e}")

# StaticFiles 마운트 — 반드시 마음이음 라우터 등록 이후에 위치 (그래야 /maeum/ 을 가로채지 않음)
if os.path.isdir(PROTOTYPE_DIR):
    app.mount('/', StaticFiles(directory=PROTOTYPE_DIR, html=True), name='static')

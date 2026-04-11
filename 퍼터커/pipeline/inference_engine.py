"""
inference_engine.py
단일 환자의 퍼터커 발성 음원(.wav)을 입력받아 마스터 모델을 통해 실시간 예측 및 점수화.
v1 모델(12 DDK + Mel + Wav2Vec2)을 활용합니다.
"""
import os
import sys
import json
import pickle
import numpy as np
import torch
import librosa
import importlib.util

# ── 모듈 경로 설정 ──────────────────────────────────────────
DATA_DIR = r"D:\퍼터커"
MODEL_DIR = os.path.join(DATA_DIR, "models", "master")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def _load_module(name, filename):
    path = os.path.join(DATA_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# 모듈 패스에 상위 디렉토리(pipeline 부모) 추가
sys.path.append(DATA_DIR)

# 기존 특성 추출 및 인코더 모듈 임포트
m_feat = _load_module("m_feat", "02_feature_extraction.py")
m_enc = _load_module("m_enc", "03_deep_encoders.py")
m_fus = _load_module("m_fus", "04_attention_fusion.py")
m_cls = _load_module("m_cls", "05-1_train_classifier.py")

# 스코어링 모듈 임포트
from pipeline import scoring

class PutterkerInferenceEngine:
    def __init__(self, use_w2v=False):
        """
        초기화 로직: 마스터 모델의 pt 가중치, 스케일러, Youden's J 임계를 메모리에 로드 (1번만 수행)
        use_w2v: True시 1.2GB 허깅페이스 모델 로드, False시 빠른 추론을 위해 영벡터로 대체
        """
        print(">> [Init] 1. 마스터 스케일러 & 임계값 로드 중...")
        with open(os.path.join(MODEL_DIR, "scaler_master.pkl"), "rb") as f:
            self.scaler = pickle.load(f)
            
        with open(os.path.join(MODEL_DIR, "thresholds.json"), "r", encoding="utf-8") as f:
            self.thresholds = json.load(f)
            
        print(">> [Init] 2. PyTorch 마스터 모델(ResNet, Fusion, MLP) 로드 중...")
        self.resnet = m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)
        self.fusion = m_fus.FeatureFusion(ddk_dim=12, w2v_dim=256, mel_dim=256, fusion_dim=256).to(DEVICE)
        self.classifier = m_cls.DysarthriaMLPClassifier(input_dim=self.fusion.total_dim, num_classes=3).to(DEVICE)
        
        self.resnet.load_state_dict(torch.load(os.path.join(MODEL_DIR, "resnet_master.pt"), map_location=DEVICE))
        self.fusion.load_state_dict(torch.load(os.path.join(MODEL_DIR, "fusion_master.pt"), map_location=DEVICE))
        self.classifier.load_state_dict(torch.load(os.path.join(MODEL_DIR, "classifier_master.pt"), map_location=DEVICE))
        
        self.resnet.eval()
        self.fusion.eval()
        self.classifier.eval()
        
        self.use_w2v = use_w2v
        if self.use_w2v:
            print(">> [Init] 3. Wav2Vec2 인코더 로드 중 (초기 로딩 지연 발생)...")
            self.w2v_model = m_enc.load_wav2vec2_encoder(device=DEVICE)
        else:
            self.w2v_model = None
            
        # LSTM Segmenter (for DDK features) 로드
        print(">> [Init] 4. DDK LSTM 분할기 로드 중...")
        self.lstm_model = m_feat.get_lstm_model(device=DEVICE)
        print(">> [Init] 엔진 준비 완료!\n")

    def predict(self, audio_path: str):
        """
        단일 오디오 파일(퍼터커)을 받아 실시간 점수 추론 수행
        """
        with torch.no_grad():
            # 1. DDK 12개 특성 실시간 추출
            ddk_feats_dict = m_feat.extract_all_features(audio_path, lstm_model=self.lstm_model, device=DEVICE)
            
            # v1 피처 순서 맞추기
            ddk_cols = [
                "f0_var_hz", "f0_var_semitones",
                "mean_energy_db", "var_energy_db", "max_energy_db",
                "ddk_rate", "ddk_mean_dur_ms", "ddk_regularity_ms",
                "pause_rate", "pause_mean_dur_ms", "pause_regularity_ms",
                "intelligibility_score"
            ]
            ddk_arr = np.array([ddk_feats_dict.get(c, 0.0) for c in ddk_cols], dtype=np.float32).reshape(1, -1)
            
            # 2. 스케일링
            ddk_scaled = self.scaler.transform(ddk_arr)
            ddk_tensor = torch.FloatTensor(ddk_scaled).to(DEVICE)
            
            # 3. Mel-Spectrogram 추출 및 ResNet 임베딩 (05-1_train_classifier 방식)
            mel_tensor = m_cls.my_audio_to_mel(audio_path, is_train=False).to(DEVICE)  # (1, 80, 400)
            mel_tensor_batch = mel_tensor.unsqueeze(0)  # (1, 1, 80, 400)
            mel_emb = self.resnet(mel_tensor_batch)     # (1, 256)
            
            # 4. Wav2Vec2 임베딩 (무거우면 영벡터 대체 가능)
            if self.use_w2v and self.w2v_model is not None:
                y, sr = librosa.load(audio_path, sr=16000, mono=True)
                w2v_input = m_enc.audio_to_wav2vec_input(y, sr=sr).to(DEVICE)
                w2v_emb = self.w2v_model(w2v_input) # (1, 256)
            else:
                w2v_emb = torch.zeros(1, 256).to(DEVICE)
            
            # 5. 성별(gender) 피처는 v1에서 0으로 패딩 (Shape: [1, 1])
            gender_tensor = torch.zeros(1, 1).to(DEVICE)
            
            # 6. Fusion & MLP 예측
            fused_vector = self.fusion(ddk_tensor, gender_tensor, mel_emb, w2v_emb)
            logits = self.classifier(fused_vector)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            
        # 7. 2단계 Youden's J 임계값 기반 순수 중증도 분류 로직 (점수화 제외)
        prob_anomaly = probs[1] + probs[2]
        if prob_anomaly < self.thresholds["thresh_binary"]:
            severity_class = 0
            severity_label = "정상"
        else:
            severe_ratio = probs[2] / (prob_anomaly + 1e-8)
            if severe_ratio >= self.thresholds["thresh_severe"]:
                severity_class = 2
                severity_label = "중증"
            else:
                severity_class = 1
                severity_label = "경증"
                
        return {
            "status": "success",
            "severity_label": severity_label,
            "severity_class": severity_class,
            "details": {
                "probs": [float(round(probs[0], 4)), float(round(probs[1], 4)), float(round(probs[2], 4))]
            }
        }


# --- 터미널 단독 실행용 테스트 ---
if __name__ == "__main__":
    import argparse
    import soundfile as sf
    print("=== Putterker 실시간 추론 엔진 테스트 ===")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=str, help="분석할 오디오 파일 경로", default="")
    args = parser.parse_args()
    
    # Wav2Vec2 없이 빠른 버전으로 로드
    engine = PutterkerInferenceEngine(use_w2v=False)
    
    test_audio = args.audio
    
    if test_audio and os.path.exists(test_audio):
        print(f"\n[입력 파일]: {test_audio}")
        
        # m4a 등 wav가 아닌 경우 변환 후 분석
        if not test_audio.lower().endswith(".wav"):
            print("  -> m4a/기타 포맷 감지됨. wav로 임시 변환 후 분석을 진행합니다.")
            y, sr = librosa.load(test_audio, sr=16000)
            temp_wav = test_audio.rsplit('.', 1)[0] + "_converted.wav"
            sf.write(temp_wav, y, sr)
            test_audio = temp_wav
            print(f"  -> 변환 완료: {temp_wav}")

        res = engine.predict(test_audio)
        print("\n[추론 결과 JSON]")
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("\n[오류] 올바른 파일 경로를 입력해주세요.")

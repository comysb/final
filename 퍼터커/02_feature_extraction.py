"""
02_feature_extraction.py
DDK 특성 추출 (12가지):
  - Phonation (5): Praat/parselmouth
  - Prosody+Respiration (7): LSTM 음절분할 모델
  - Intelligibility (1): Whisper WER 기반
"""
import os
import numpy as np
import librosa
import parselmouth
from parselmouth.praat import call
import torch
import torch.nn as nn
import whisper
import warnings
warnings.filterwarnings("ignore")

SR = 16000

# ─────────────────────────────────────────────
# 1. 발성 특성 (Phonation) - Praat
# ─────────────────────────────────────────────

def extract_phonation(audio_path):
    """F0 변동성, 에너지 관련 5가지 특성 추출"""
    snd = parselmouth.Sound(audio_path)
    snd = snd.resample(SR)

    # Pitch (F0)
    pitch = call(snd, "To Pitch", 0.0, 50, 600)
    pitch_values = pitch.selected_array['frequency']
    pitch_values = pitch_values[pitch_values > 0]

    if len(pitch_values) < 2:
        f0_var_st = 0.0
        f0_var_hz = 0.0
    else:
        # F0 변동성 (Hz)
        f0_var_hz = float(np.std(pitch_values))
        # F0 변동성 (semitones) - 반음 변환
        pitch_st = 12 * np.log2(pitch_values / (pitch_values.mean() + 1e-8) + 1e-8)
        f0_var_st = float(np.std(pitch_st))

    # 에너지 (Intensity)
    intensity = call(snd, "To Intensity", 75, 0.0, "yes")
    int_values = intensity.values.flatten()
    int_values = int_values[int_values > 0]

    if len(int_values) < 1:
        mean_energy = 0.0
        var_energy = 0.0
        max_energy = 0.0
    else:
        mean_energy = float(np.mean(int_values))
        var_energy = float(np.std(int_values))
        max_energy = float(np.max(int_values))

    return {
        "f0_var_hz": f0_var_hz,
        "f0_var_semitones": f0_var_st,
        "mean_energy_db": mean_energy,
        "var_energy_db": var_energy,
        "max_energy_db": max_energy,
    }


# ─────────────────────────────────────────────
# 2. LSTM 음절분할 모델 (16층)
# ─────────────────────────────────────────────

class LSTMSyllableSegmenter(nn.Module):
    """16층 LSTM + FC → 프레임별 Speech/Non-speech 이진 분류"""
    def __init__(self, input_size=80, hidden_size=128, num_layers=16, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True,
        )
        self.fc = nn.Linear(hidden_size * 2, 1)  # bidirectional → *2
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)       # (B, T, H*2)
        out = self.fc(out)          # (B, T, 1)
        return self.sigmoid(out).squeeze(-1)  # (B, T)


MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
LSTM_MODEL_PATH = os.path.join(MODEL_DIR, "lstm_segmenter.pt")

def get_lstm_model(device="cpu"):
    model = LSTMSyllableSegmenter()
    if os.path.exists(LSTM_MODEL_PATH):
        model.load_state_dict(torch.load(LSTM_MODEL_PATH, map_location=device))
        print("  LSTM 가중치 로드 완료")
    else:
        print("  [INFO] LSTM 사전학습 가중치 없음 → 랜덤 초기화로 특성 추출 (학습 필요)")
    model.eval()
    return model.to(device)


def audio_to_melspec(y, sr=SR, n_mels=80, hop_length=160):
    """오디오 → Mel-Spectrogram (T x n_mels)"""
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, hop_length=hop_length)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    return mel_db.T  # (T, n_mels)


def segment_syllables(y, model, sr=SR, device="cpu",
                       speech_min_dur=0.07, pause_min_dur=0.14, hop_length=160):
    """LSTM으로 음절/휴지 구간 분할"""
    mel = audio_to_melspec(y, sr=sr, hop_length=hop_length)
    mel_tensor = torch.FloatTensor(mel).unsqueeze(0).to(device)  # (1, T, 80)

    with torch.no_grad():
        probs = model(mel_tensor).squeeze(0).cpu().numpy()  # (T,)

    frame_dur = hop_length / sr  # 초
    labels = (probs > 0.5).astype(int)

    # 연속 구간 검출
    speech_segs = []
    pause_segs = []
    start = 0
    cur_label = labels[0]

    for i in range(1, len(labels)):
        if labels[i] != cur_label:
            dur = (i - start) * frame_dur
            seg = {"start": start * frame_dur, "end": i * frame_dur, "dur": dur}
            if cur_label == 1 and dur >= speech_min_dur:
                speech_segs.append(seg)
            elif cur_label == 0 and dur >= pause_min_dur:
                pause_segs.append(seg)
            start = i
            cur_label = labels[i]

    return speech_segs, pause_segs


def extract_prosody_respiration(y, model, sr=SR, device="cpu"):
    """운율(3) + 호흡(3) = 7가지 → 총 6가지 + 속도"""
    speech_segs, pause_segs = segment_syllables(y, model, sr=sr, device=device)
    total_dur = len(y) / sr

    n_syllables = len(speech_segs)

    # Prosody
    ddk_rate = n_syllables / total_dur if total_dur > 0 else 0.0
    durations = [s["dur"] for s in speech_segs] if speech_segs else [0.0]
    ddk_mean_dur = float(np.mean(durations)) * 1000  # ms
    ddk_regularity = float(np.std(durations)) * 1000  # ms (표준편차)

    # Respiration
    n_pauses = len(pause_segs)
    pause_rate = n_pauses / total_dur if total_dur > 0 else 0.0
    p_durations = [p["dur"] for p in pause_segs] if pause_segs else [0.0]
    pause_mean_dur = float(np.mean(p_durations)) * 1000  # ms
    pause_regularity = float(np.std(p_durations)) * 1000  # ms

    return {
        "ddk_rate": ddk_rate,
        "ddk_mean_dur_ms": ddk_mean_dur,
        "ddk_regularity_ms": ddk_regularity,
        "pause_rate": pause_rate,
        "pause_mean_dur_ms": pause_mean_dur,
        "pause_regularity_ms": pause_regularity,
    }


# ─────────────────────────────────────────────
# 3. 명료도 점수 - Whisper WER 기반
# ─────────────────────────────────────────────

_whisper_model = None

def get_whisper_model(model_size="base"):
    global _whisper_model
    if _whisper_model is None:
        print("  Whisper 모델 로드 중...")
        _whisper_model = whisper.load_model(model_size)
    return _whisper_model


def extract_intelligibility(audio_path):
    """
    Whisper로 발화 전사 후 명료도 점수 계산.
    DDK 과제(/pa/ 반복)는 단순 반복이므로 신뢰도 기반 점수 사용.
    점수 범위: 0~100 (높을수록 명료도 높음)
    """
    try:
        wmodel = get_whisper_model("base")
        result = wmodel.transcribe(audio_path, language="ko", fp16=False)
        # 평균 no_speech_prob 기반 명료도 (반전)
        segments = result.get("segments", [])
        if segments:
            no_speech_probs = [s.get("no_speech_prob", 0.5) for s in segments]
            avg_no_speech = np.mean(no_speech_probs)
            score = (1.0 - avg_no_speech) * 100.0
        else:
            score = 50.0  # 기본값
    except Exception as e:
        print(f"  [Whisper 오류] {e}")
        score = 50.0

    return {"intelligibility_score": float(score)}


# ─────────────────────────────────────────────
# 4. 전체 특성 추출 함수
# ─────────────────────────────────────────────

def extract_all_features(audio_path, lstm_model=None, device="cpu"):
    """
    12가지 DDK 특성 추출
    Returns: dict (12 features)
    """
    y, _ = librosa.load(audio_path, sr=SR, mono=True)

    # 1. Phonation (5)
    phon = extract_phonation(audio_path)

    # 2. Prosody + Respiration (6)
    if lstm_model is None:
        lstm_model = get_lstm_model(device)
    pros_resp = extract_prosody_respiration(y, lstm_model, device=device)

    # 3. Intelligibility (1)
    intel = extract_intelligibility(audio_path)

    features = {**phon, **pros_resp, **intel}
    return features


FEATURE_NAMES = [
    "f0_var_hz",
    "f0_var_semitones",
    "mean_energy_db",
    "var_energy_db",
    "max_energy_db",
    "ddk_rate",
    "ddk_mean_dur_ms",
    "ddk_regularity_ms",
    "pause_rate",
    "pause_mean_dur_ms",
    "pause_regularity_ms",
    "intelligibility_score",
]


if __name__ == "__main__":
    import pandas as pd

    DATA_DIR = r"D:\모델1"
    df = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    sample_path = df["path"].iloc[0]

    print(f"특성 추출 테스트: {os.path.basename(sample_path)}")
    feats = extract_all_features(sample_path)
    for k, v in feats.items():
        print(f"  {k}: {v:.4f}")

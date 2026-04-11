"""
03_deep_encoders.py
딥러닝 음성 인코더:
  - Mel-Spectrogram → ResNet18 → 임베딩
  - Raw Audio → Wav2vec2 XLS-R-300M → 임베딩
"""
import os
import numpy as np
import torch
import torch.nn as nn
import torchaudio
import torchaudio.transforms as T
import librosa
from transformers import Wav2Vec2Model, Wav2Vec2FeatureExtractor
import warnings
warnings.filterwarnings("ignore")

SR = 16000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ─────────────────────────────────────────────
# 1. Mel-Spectrogram → ResNet18 인코더
# ─────────────────────────────────────────────

class ResNetMelEncoder(nn.Module):
    """
    Mel-Spectrogram(80 mel, 3채널 복제) → ResNet18 Backbone → 임베딩 벡터
    """
    def __init__(self, embedding_dim=256):
        super().__init__()
        import torchvision.models as models
        resnet = models.resnet18(weights=None)
        # 첫 번째 conv 수정: 1채널 입력
        resnet.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        # FC 레이어 교체
        resnet.fc = nn.Linear(resnet.fc.in_features, embedding_dim)
        self.backbone = resnet
        self.embedding_dim = embedding_dim

    def forward(self, mel):
        """
        mel: (B, 1, n_mels, T) or (B, n_mels, T)
        returns: (B, embedding_dim)
        """
        if mel.dim() == 3:
            mel = mel.unsqueeze(1)  # (B, 1, n_mels, T)
        return self.backbone(mel)


def audio_to_melspec_tensor(y, sr=SR, n_mels=80, n_fft=512, hop_length=160, max_frames=400):
    """오디오 배열 → Mel-Spectrogram 텐서 (1, n_mels, T)"""
    mel = librosa.feature.melspectrogram(
        y=y, sr=sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop_length
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)  # (n_mels, T)

    # 길이 고정 (패딩 or 자르기)
    if mel_db.shape[1] < max_frames:
        pad_width = max_frames - mel_db.shape[1]
        mel_db = np.pad(mel_db, ((0, 0), (0, pad_width)), mode="constant")
    else:
        mel_db = mel_db[:, :max_frames]

    mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-8)  # 정규화
    return torch.FloatTensor(mel_db).unsqueeze(0)  # (1, n_mels, T)


# ─────────────────────────────────────────────
# 2. Wav2vec2 XLS-R-300M 인코더
# ─────────────────────────────────────────────

WAV2VEC_MODEL = "facebook/wav2vec2-xls-r-300m"

class Wav2Vec2Encoder(nn.Module):
    """
    Raw Audio → Wav2vec2 XLS-R-300M → 프레임 임베딩 평균 → 임베딩 벡터
    """
    def __init__(self, embedding_dim=256):
        super().__init__()
        self.wav2vec2 = Wav2Vec2Model.from_pretrained(WAV2VEC_MODEL)
        # XLS-R-300M hidden size = 1024
        self.projection = nn.Linear(1024, embedding_dim)
        self.embedding_dim = embedding_dim

    def forward(self, input_values, attention_mask=None):
        """
        input_values: (B, T_audio) raw waveform
        returns: (B, embedding_dim)
        """
        outputs = self.wav2vec2(
            input_values=input_values,
            attention_mask=attention_mask,
            output_hidden_states=False,
        )
        # last_hidden_state: (B, T_frames, 1024)
        frame_embeddings = outputs.last_hidden_state
        # 시간 평균 풀링
        pooled = frame_embeddings.mean(dim=1)  # (B, 1024)
        return self.projection(pooled)          # (B, embedding_dim)


def load_wav2vec2_encoder(device=DEVICE):
    print("  Wav2vec2 XLS-R-300M 로드 중... (첫 실행시 다운로드 필요)")
    model = Wav2Vec2Encoder().to(device)
    model.eval()
    return model


def audio_to_wav2vec_input(y, sr=SR, max_length=16000 * 10):
    """오디오 배열 → Wav2vec2 입력 텐서 (1, T)"""
    if len(y) > max_length:
        y = y[:max_length]
    return torch.FloatTensor(y).unsqueeze(0)  # (1, T)


# ─────────────────────────────────────────────
# 3. 배치 특성 추출 유틸
# ─────────────────────────────────────────────

@torch.no_grad()
def extract_deep_features(audio_paths, mel_encoder, wav2vec_encoder, device=DEVICE, batch_size=4):
    """
    여러 오디오 파일에서 Mel + Wav2vec 임베딩 추출
    Returns:
        mel_embeds: (N, mel_dim)
        w2v_embeds: (N, w2v_dim)
    """
    mel_encoder.eval()
    wav2vec_encoder.eval()

    all_mel, all_w2v = [], []

    for i in range(0, len(audio_paths), batch_size):
        batch_paths = audio_paths[i:i+batch_size]
        mel_batch, w2v_batch = [], []

        for path in batch_paths:
            y, _ = librosa.load(path, sr=SR, mono=True)
            mel_t = audio_to_melspec_tensor(y).to(device)          # (1, n_mels, T)
            w2v_t = audio_to_wav2vec_input(y).to(device)           # (1, T)
            mel_batch.append(mel_t)
            w2v_batch.append(w2v_t)

        # Mel 배치
        mel_batch_t = torch.stack(mel_batch, dim=0)                # (B, 1, n_mels, T)
        mel_emb = mel_encoder(mel_batch_t)                         # (B, mel_dim)

        # Wav2vec 배치 (가변 길이 → 패딩)
        max_len = max(t.shape[1] for t in w2v_batch)
        w2v_padded = torch.zeros(len(w2v_batch), max_len).to(device)
        for j, t in enumerate(w2v_batch):
            w2v_padded[j, :t.shape[1]] = t[0]
        w2v_emb = wav2vec_encoder(w2v_padded)                      # (B, w2v_dim)

        all_mel.append(mel_emb.cpu())
        all_w2v.append(w2v_emb.cpu())
        print(f"  처리: {min(i+batch_size, len(audio_paths))}/{len(audio_paths)}")

    return torch.cat(all_mel, dim=0), torch.cat(all_w2v, dim=0)


if __name__ == "__main__":
    import pandas as pd
    DATA_DIR = r"D:\모델1"
    df = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    sample_paths = df["path"].iloc[:2].tolist()

    mel_enc = ResNetMelEncoder().to(DEVICE)
    w2v_enc = load_wav2vec2_encoder(DEVICE)

    mel_emb, w2v_emb = extract_deep_features(sample_paths, mel_enc, w2v_enc, DEVICE)
    print(f"Mel 임베딩 shape: {mel_emb.shape}")
    print(f"Wav2vec 임베딩 shape: {w2v_emb.shape}")

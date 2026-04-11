"""
05-1_train_classifier.py
MLP 분류기 학습 + Online SpecAugment (ResNet 종단간 학습 포함)
  - 입력: 오디오 Path -> Mel 변환 -> SpecAugment -> ResNet -> 임베딩 -> Fusion
  - 3-class 분류 + 새로운 평가지표 산출 (Sensitivity, Specificity, AUC, Kappa)
"""
import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.utils.class_weight import compute_class_weight
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score, cohen_kappa_score
import librosa
import torchaudio.transforms as T
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = r"D:\모델1"
MODEL_DIR = os.path.join(DATA_DIR, "models_1")
os.makedirs(MODEL_DIR, exist_ok=True)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

time_masking = T.TimeMasking(time_mask_param=30)
freq_masking = T.FrequencyMasking(freq_mask_param=15)

def my_audio_to_mel(path, is_train=False):
    """실시간 오디오 로드 및 Mel 변환, 학습 시 SpecAugment 적용"""
    y, _ = librosa.load(path, sr=16000, mono=True)
    mel = librosa.feature.melspectrogram(y=y, sr=16000, n_mels=80, n_fft=512, hop_length=160)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    
    max_frames = 400
    if mel_db.shape[1] < max_frames:
        mel_db = np.pad(mel_db, ((0, 0), (0, max_frames - mel_db.shape[1])))
    else:
        mel_db = mel_db[:, :max_frames]
        
    mel_db = (mel_db - mel_db.mean()) / (mel_db.std() + 1e-8)
    tensor_mel = torch.FloatTensor(mel_db).unsqueeze(0) # (1, 80, 400)
    
    if is_train:
        tensor_mel = time_masking(tensor_mel)
        tensor_mel = freq_masking(tensor_mel)
        
    return tensor_mel


# ─────────────────────────────────────────────
# 1. Dataset
# ─────────────────────────────────────────────

class DysarthriaOnlineDataset(Dataset):
    def __init__(self, feature_df, scaler=None, fit_scaler=False, is_train=False):
        """
        feature_df: CSV with columns [path, label, f0_var_hz, ..., w2v_emb_*] (features_emb_1.csv 형태)
        """
        self.paths = feature_df["path"].values
        self.labels = torch.LongTensor(feature_df["label"].values)
        self.is_train = is_train

        # DDK 12 특성 (전체 사용: Phonation 5 + Prosody/Respiration 6 + Intelligibility 1)
        ddk_cols = [
            # Phonation - Praat (5)
            "f0_var_hz", "f0_var_semitones",
            "mean_energy_db", "var_energy_db", "max_energy_db",
            # Prosody + Respiration - LSTM (6)
            "ddk_rate", "ddk_mean_dur_ms", "ddk_regularity_ms",
            "pause_rate", "pause_mean_dur_ms", "pause_regularity_ms",
            # Intelligibility - Whisper (1)
            "intelligibility_score",
        ]
        # 누락된 컬럼은 0으로 채움 (CSV에 없을 경우 대비)
        for col in ddk_cols:
            if col not in feature_df.columns:
                feature_df = feature_df.copy()
                feature_df[col] = 0.0
        ddk_data = feature_df[ddk_cols].values.astype(np.float32)

        if fit_scaler:
            scaler = StandardScaler()
            ddk_data = scaler.fit_transform(ddk_data)
        elif scaler is not None:
            ddk_data = scaler.transform(ddk_data)

        self.scaler = scaler
        self.ddk = torch.FloatTensor(ddk_data)

        # 성별 (없으면 0)
        if "gender" in feature_df.columns:
            self.gender = torch.FloatTensor(feature_df["gender"].values).unsqueeze(1)
        else:
            self.gender = torch.zeros(len(feature_df), 1)

        # Wav2vec 임베딩 (오프라인 캐싱값 사용)
        w2v_cols = [c for c in feature_df.columns if c.startswith("w2v_")]
        if w2v_cols:
            self.w2v = torch.FloatTensor(feature_df[w2v_cols].values.astype(np.float32))
        else:
            self.w2v = torch.zeros(len(feature_df), 256)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        path = self.paths[idx]
        mel_tensor = my_audio_to_mel(path, is_train=self.is_train)
        return {
            "path": path,
            "ddk": self.ddk[idx],
            "gender": self.gender[idx],
            "mel": mel_tensor,   
            "w2v": self.w2v[idx],
            "label": self.labels[idx],
        }


# ─────────────────────────────────────────────
# 2. 모델 구조
# ─────────────────────────────────────────────

class DysarthriaMLPClassifier(nn.Module):
    def __init__(self, input_dim=525, hidden_dim=256, num_classes=3, dropout=0.3):
        # 입력 차원: DDK 12 + gender 1 + mel_emb 256 + att_fused 256 = 525
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes),
        )

    def forward(self, x):
        return self.net(x)

def build_input(batch, fusion_module, resnet_model, device):
    """온라인 Mel 텐서를 ResNet에 통과시키고 융합"""
    ddk = batch["ddk"].to(device)
    gender = batch["gender"].to(device)
    mel_tensor = batch["mel"].to(device)  # (B, 1, 80, 400)
    w2v = batch["w2v"].to(device)
    
    mel_emb = resnet_model(mel_tensor)    # (B, 256)
    return fusion_module(ddk, gender, mel_emb, w2v)


# ─────────────────────────────────────────────
# 3. 학습 루프
# ─────────────────────────────────────────────

def train_classifier(train_df, val_df, num_epochs=100, batch_size=16, lr=3e-5):
    import importlib.util
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import CosineAnnealingLR
    
    # 04_attention_fusion 로드
    _s_fus = importlib.util.spec_from_file_location("m_fus", os.path.join(DATA_DIR, "04_attention_fusion.py"))
    m_fus  = importlib.util.module_from_spec(_s_fus)
    _s_fus.loader.exec_module(m_fus)
    
    # 03_deep_encoders 로드 (ResNet)
    _s_enc = importlib.util.spec_from_file_location("m_enc", os.path.join(DATA_DIR, "03_deep_encoders.py"))
    m_enc  = importlib.util.module_from_spec(_s_enc)
    _s_enc.loader.exec_module(m_enc)

    # 데이터셋
    train_dataset = DysarthriaOnlineDataset(train_df, fit_scaler=True, is_train=True)
    scaler = train_dataset.scaler
    val_dataset = DysarthriaOnlineDataset(val_df, scaler=scaler, is_train=False)

    # 파일로 scaler 저장
    with open(os.path.join(MODEL_DIR, "scaler_1.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # 클래스 가중치
    labels = train_df["label"].values
    weights = compute_class_weight("balanced", classes=np.unique(labels), y=labels)
    class_weights = torch.FloatTensor(weights).to(DEVICE)

    # 모델 생성
    resnet = m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)
    fusion = m_fus.FeatureFusion(mel_dim=256, w2v_dim=256, fusion_dim=256).to(DEVICE)
    classifier = DysarthriaMLPClassifier(input_dim=fusion.total_dim, num_classes=3).to(DEVICE)

    # Optimizer (ResNet까지 통째로 학습)
    all_params = list(resnet.parameters()) + list(fusion.parameters()) + list(classifier.parameters())
    optimizer = AdamW(all_params, lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=num_epochs)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    best_val_acc = 0.0

    print("▶ 온라인 증강 학습 시작...")
    for epoch in range(num_epochs):
        # Train
        resnet.train(); fusion.train(); classifier.train()
        t_losses, t_preds, t_trues = [], [], []

        for batch in train_loader:
            optimizer.zero_grad()
            x = build_input(batch, fusion, resnet, DEVICE)
            logits = classifier(x)
            loss = criterion(logits, batch["label"].to(DEVICE))
            loss.backward()
            nn.utils.clip_grad_norm_(all_params, 1.0)
            optimizer.step()

            t_losses.append(loss.item())
            t_preds.extend(logits.argmax(1).cpu().numpy())
            t_trues.extend(batch["label"].numpy())

        # Val
        resnet.eval(); fusion.eval(); classifier.eval()
        v_losses, v_preds, v_trues = [], [], []
        with torch.no_grad():
            for batch in val_loader:
                x = build_input(batch, fusion, resnet, DEVICE)
                logits = classifier(x)
                loss = criterion(logits, batch["label"].to(DEVICE))
                v_losses.append(loss.item())
                v_preds.extend(logits.argmax(1).cpu().numpy())
                v_trues.extend(batch["label"].numpy())

        train_acc = accuracy_score(t_trues, t_preds)
        val_acc = accuracy_score(v_trues, v_preds)
        history["train_loss"].append(np.mean(t_losses))
        history["val_loss"].append(np.mean(v_losses))
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        scheduler.step()

        if (epoch + 1) % 10 == 0:
            print(f"  [Epoch {epoch+1:3d}/{num_epochs}] Train Loss: {np.mean(t_losses):.4f} Acc: {train_acc:.4f} | Val Loss: {np.mean(v_losses):.4f} Acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(resnet.state_dict(), os.path.join(MODEL_DIR, "resnet_best_1.pt"))
            torch.save(fusion.state_dict(), os.path.join(MODEL_DIR, "fusion_best_1.pt"))
            torch.save(classifier.state_dict(), os.path.join(MODEL_DIR, "classifier_best_1.pt"))

    history["train_loss"] = [float(x) for x in history["train_loss"]]
    history["val_loss"] = [float(x) for x in history["val_loss"]]
    with open(os.path.join(MODEL_DIR, "history_1.json"), "w") as f:
        json.dump(history, f, indent=2)

    # 4. Mel 저장용 로직 (XAI 분석을 위해 최종 Train/Test Set의 Mel 임베딩을 CSV로 고정해줍니다)
    # 왜냐하면 XAI는 엑셀에 있는 데이터를 받기 때문입니다.
    def _save_offline_mels(df, path_name):
        ds = DysarthriaOnlineDataset(df, scaler=scaler, is_train=False) # specaugment off
        bs = 16
        dl = DataLoader(ds, batch_size=bs, shuffle=False)
        resnet.eval()
        all_mel_feats = []
        with torch.no_grad():
            for b in dl:
                m_ten = b["mel"].to(DEVICE)
                emb = resnet(m_ten)
                all_mel_feats.append(emb.cpu().numpy())
        final_mels = np.concatenate(all_mel_feats, axis=0)
        # 기본 코드 호환성을 위해 새 컬럼 할당
        for i in range(256):
            df[f"mel_{i}"] = final_mels[:, i]
        df.to_csv(path_name, index=False, encoding="utf-8-sig")

    print("\n최종 학습 완료. XAI 연동을 위한 임베딩 캐싱 갱신 중...")
    _save_offline_mels(train_df, os.path.join(DATA_DIR, "features_emb_train_1.csv"))
    _save_offline_mels(val_df, os.path.join(DATA_DIR, "features_emb_val_1.csv"))

    return resnet, fusion, classifier, scaler, history


def evaluate(test_df, resnet, fusion, classifier, scaler, device=DEVICE):
    """
    2단계 Youden's J 평가:
      Step 1) 정상 vs 비정상 → 이진 Youden's J로 thresh_binary 도출
      Step 2) 비정상 중 경증 vs 중증 → 중증 전용 Youden's J로 thresh_severe 도출
    """
    from sklearn.metrics import roc_curve
    test_dataset = DysarthriaOnlineDataset(test_df, scaler=scaler, is_train=False)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

    resnet.eval(); fusion.eval(); classifier.eval()
    all_probs, all_trues = [], []

    with torch.no_grad():
        for batch in test_loader:
            x = build_input(batch, fusion, resnet, device)
            logits = classifier(x)
            probs = F.softmax(logits, dim=1)
            all_probs.extend(probs.cpu().numpy())
            all_trues.extend(batch["label"].numpy())

    all_probs = np.array(all_probs)
    all_trues = np.array(all_trues)

    # ── Step 1: 정상 vs 비정상 Youden's J ──────────────────────────
    anomaly_probs = all_probs[:, 1] + all_probs[:, 2]
    binary_trues  = np.where(all_trues >= 1, 1, 0)
    try:
        fpr, tpr, thr = roc_curve(binary_trues, anomaly_probs)
        thresh_binary = float(thr[np.argmax(tpr - fpr)])
    except Exception:
        thresh_binary = 0.5

    # ── Step 2: 중증 전용 Youden's J ────────────────────────────────
    severe_ratio = np.where(
        (all_probs[:, 1] + all_probs[:, 2]) > 0,
        all_probs[:, 2] / (all_probs[:, 1] + all_probs[:, 2] + 1e-8),
        0.0
    )
    severe_trues = np.where(all_trues == 2, 1, 0)
    try:
        fpr_s, tpr_s, thr_s = roc_curve(severe_trues, severe_ratio)
        thresh_severe = float(thr_s[np.argmax(tpr_s - fpr_s)])
    except Exception:
        thresh_severe = 0.5

    print(f"\n  ▶ [2단계 Youden's J] thresh_binary={thresh_binary:.4f} | thresh_severe={thresh_severe:.4f}")

    # ── 최종 판정 ───────────────────────────────────────────────────
    final_preds = []
    for i in range(len(all_trues)):
        if anomaly_probs[i] < thresh_binary:
            final_preds.append(0)
        else:
            final_preds.append(2 if severe_ratio[i] >= thresh_severe else 1)
    all_preds = np.array(final_preds)

    # ── 지표 계산 ───────────────────────────────────────────────────
    micro_acc = accuracy_score(all_trues, all_preds)
    cm = confusion_matrix(all_trues, all_preds, labels=[0, 1, 2])
    with np.errstate(divide='ignore', invalid='ignore'):
        per_class_acc = np.nan_to_num(cm.diagonal() / cm.sum(axis=1))
    macro_acc = float(np.mean(per_class_acc))

    sensitivities, specificities = [], []
    for i in range(3):
        tp = cm[i, i]
        fn = np.sum(cm[i, :]) - tp
        fp = np.sum(cm[:, i]) - tp
        tn = np.sum(cm) - (tp + fp + fn)
        sensitivities.append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)
        specificities.append(tn / (tn + fp) if (tn + fp) > 0 else 0.0)

    sensitivity = float(np.mean(sensitivities))
    specificity = float(np.mean(specificities))

    try:
        roc_auc_multi  = float(roc_auc_score(all_trues, all_probs, multi_class="ovr"))
        roc_auc_binary = float(roc_auc_score(binary_trues, anomaly_probs))
    except Exception:
        roc_auc_multi, roc_auc_binary = 0.0, 0.0

    kappa = float(cohen_kappa_score(all_trues, all_preds))

    print(f"\n=== 최종 테스트 결과 (2단계 Youden's J / 12 DDK 피처) ===")
    print(f"Micro Accuracy : {micro_acc*100:.2f}%")
    print(f"Macro Accuracy : {macro_acc*100:.2f}%")
    print(f"Sensitivity    : {sensitivity*100:.2f}%  "
          f"[정상:{sensitivities[0]*100:.1f}% 경증:{sensitivities[1]*100:.1f}% 중증:{sensitivities[2]*100:.1f}%]")
    print(f"Specificity    : {specificity*100:.2f}%")
    print(f"ROC-AUC (OVR)  : {roc_auc_multi:.4f}")
    print(f"ROC-AUC (Bin)  : {roc_auc_binary:.4f}")
    print(f"Cohen's Kappa  : {kappa:.4f}")
    print(f"Confusion Matrix:\n{cm}")

    results = {
        "thresh_binary":             float(thresh_binary),
        "thresh_severe":             float(thresh_severe),
        "micro_acc":                 float(micro_acc),
        "macro_acc":                 float(macro_acc),
        "sensitivity":               float(sensitivity),
        "specificity":               float(specificity),
        "sensitivity_per_class":     [float(s) for s in sensitivities],
        "roc_auc_multi":             float(roc_auc_multi),
        "roc_auc_binary":            float(roc_auc_binary),
        "cohen_kappa":               float(kappa),
        "confusion_matrix":          cm.tolist(),
        "predictions":               [int(x) for x in all_preds],
        "true_labels":               [int(x) for x in all_trues],
    }
    with open(os.path.join(MODEL_DIR, "test_results_1.json"), "w") as f:
        json.dump(results, f, indent=2)

    # XAI용 Mel 임베딩 캐싱
    ds = DysarthriaOnlineDataset(test_df, scaler=scaler, is_train=False)
    dl = DataLoader(ds, batch_size=16, shuffle=False)
    all_mel_feats = []
    resnet.eval()
    with torch.no_grad():
        for b in dl:
            emb = resnet(b["mel"].to(device))
            all_mel_feats.append(emb.cpu().numpy())
    final_mels = np.concatenate(all_mel_feats, axis=0)
    test_df = test_df.copy()
    for i in range(256):
        test_df[f"mel_{i}"] = final_mels[:, i]
    test_df.to_csv(os.path.join(DATA_DIR, "features_emb_test_1.csv"), index=False, encoding="utf-8-sig")

    return results

if __name__ == "__main__":
    train_df = pd.read_csv(os.path.join(DATA_DIR, "features_emb_train_1.csv"))
    val_df   = pd.read_csv(os.path.join(DATA_DIR, "features_emb_val_1.csv"))
    test_df  = pd.read_csv(os.path.join(DATA_DIR, "features_emb_test_1.csv"))


    resnet, fusion, classifier, scaler, history = train_classifier(train_df, val_df)
    results = evaluate(test_df, resnet, fusion, classifier, scaler)

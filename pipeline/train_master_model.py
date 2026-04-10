"""
train_master_model.py
v1 버전을 베이스 (12개 DDK 피처 + Mel + Wav2Vec2, 나이/성별 제외)
100% 데이터를 훈련하여 마스터 모델 가중치와 스케일러(pkl), Youden's J 임계값(json)을 Freeze
"""
import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_curve
import importlib.util
import warnings
warnings.filterwarnings("ignore")

# ── 경로 및 임포트 설정 ─────────────────────────────────────
DATA_DIR = r"D:\퍼터커"
MODEL_DIR = os.path.join(DATA_DIR, "models", "master")
os.makedirs(MODEL_DIR, exist_ok=True)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def _load_module(name, filename):
    path = os.path.join(DATA_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# v1 모델 참조
m_enc = _load_module("m_enc", "03_deep_encoders.py")
m_fus = _load_module("m_fus", "04_attention_fusion.py")
m_cls = _load_module("m_cls", "05-1_train_classifier.py")

def compute_inv_freq_weights(labels, num_classes=3):
    counts = np.bincount(labels, minlength=num_classes).astype(np.float32)
    counts = np.maximum(counts, 1)
    weights = 1.0 / counts
    weights = weights / weights.sum() * num_classes  # Normalize
    return torch.FloatTensor(weights).to(DEVICE)

def evaluate_thresholds_on_train(data_loader, resnet, fusion, classifier, device):
    """학습된 모델에 전체 Train 데이터를 다시 태워, 가장 적합한 임계값을 추출"""
    resnet.eval(); fusion.eval(); classifier.eval()
    all_trues, all_probs = [], []

    with torch.no_grad():
        for batch in data_loader:
            x = m_cls.build_input(batch, fusion, resnet, device)
            logits = classifier(x)
            probs = torch.softmax(logits, dim=1)
            all_trues.extend(batch["label"].numpy())
            all_probs.extend(probs.cpu().numpy())

    all_probs = np.array(all_probs)
    all_trues = np.array(all_trues)

    # 1. 정상 vs 비정상 (Binary Youden's J)
    anomaly_probs = all_probs[:, 1] + all_probs[:, 2]
    binary_trues = np.where(all_trues >= 1, 1, 0)
    try:
        fpr, tpr, thresh = roc_curve(binary_trues, anomaly_probs)
        thresh_binary = float(thresh[np.argmax(tpr - fpr)])
    except:
        thresh_binary = 0.45

    # 2. 경증 vs 중증 (Severe Youden's J)
    severe_ratio = np.where(
        anomaly_probs > 0,
        all_probs[:, 2] / (anomaly_probs + 1e-8),
        0.0
    )
    severe_trues = np.where(all_trues == 2, 1, 0)
    try:
        fpr_s, tpr_s, thresh_s = roc_curve(severe_trues, severe_ratio)
        thresh_severe = float(thresh_s[np.argmax(tpr_s - fpr_s)])
    except:
        thresh_severe = 0.60

    return thresh_binary, thresh_severe

def main():
    print("=" * 60)
    print(" 👑 퍼터커 마스터 모델 지식 응축 (Phase 1)")
    print("    - 모델 v1 (12 DDK + Mel + Wav2Vec2) 기반")
    print(f"    - 저장 경로: {MODEL_DIR}")
    print("=" * 60)
    
    # ── 1. 데이터 로딩 ───────────────────────────────────────────
    df_all_path = os.path.join(DATA_DIR, "features_emb_all.csv")
    aug_pool_path = os.path.join(DATA_DIR, "features_emb_aug_pool.csv")
    
    df_all = pd.read_csv(df_all_path)
    if "uid" not in df_all.columns:
        df_all["uid"] = df_all["path"].apply(lambda x: os.path.basename(x).replace(".wav", ""))

    df_aug = pd.read_csv(aug_pool_path)
    
    print("▶ 1. 100% 전체 데이터셋 준비 중...")
    severe_uids = df_all[df_all["label"] == 2]["uid"].tolist()
    matched_augs = df_aug[df_aug["original_uid"].isin(severe_uids)] if "original_uid" in df_aug.columns else df_aug.copy()
    
    # 영혼까지 끌어모은 100% 데이터셋 병합
    train_df = pd.concat([df_all, matched_augs], ignore_index=True)
    train_df = train_df.fillna(0)
    train_df = train_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    v_counts = train_df["label"].value_counts().sort_index()
    print(f"  [최종 학습 데이터 분포] 정상={v_counts.get(0,0)}, 경증={v_counts.get(1,0)}, 중증={v_counts.get(2,0)}")

    # 경로를 현재 DATA_DIR 기준으로 맞춤
    OLD_PATHS = [r"D:\모델1", r"D:\퍼터커"]
    for old in OLD_PATHS:
        train_df["path"] = train_df["path"].str.replace(old, DATA_DIR, regex=False)
        
    # ── 2. 모델 및 데이터로더 준비 ────────────────────────────────
    resnet = m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)
    w2v_dim = sum(1 for c in train_df.columns if c.startswith("w2v_")) or 256
    
    # v1 구조의 FeatureFusion (12 DDK + 256 W2V + 256 Mel)
    fusion = m_fus.FeatureFusion(ddk_dim=12, w2v_dim=w2v_dim, mel_dim=256, fusion_dim=256).to(DEVICE)
    classifier = m_cls.DysarthriaMLPClassifier(input_dim=fusion.total_dim, num_classes=3).to(DEVICE)
    
    print("▶ 2. 데이터 전처리 및 Scaler 피팅 완료")
    # v1의 DysarthriaOnlineDataset 사용
    train_dataset = m_cls.DysarthriaOnlineDataset(train_df, fit_scaler=True, is_train=True)
    scaler = train_dataset.scaler
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=16, shuffle=True)
    
    # 스케일러 저장
    scaler_path = os.path.join(MODEL_DIR, "scaler_master.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    
    # 가중치 밸런싱
    fold_labels = train_df["label"].values.astype(int)
    class_weights = compute_inv_freq_weights(fold_labels)
    
    optimizer = torch.optim.AdamW(
        list(resnet.parameters()) + list(fusion.parameters()) + list(classifier.parameters()),
        lr=3e-5, weight_decay=1e-4
    )
    from torch.optim.lr_scheduler import CosineAnnealingLR
    scheduler = CosineAnnealingLR(optimizer, T_max=100)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    all_params = list(resnet.parameters()) + list(fusion.parameters()) + list(classifier.parameters())
    
    print("\n▶ 3. 딥러닝 마스터 모델 학습 진행 중 (100 Epochs)...")
    for epoch in range(100):
        resnet.train(); fusion.train(); classifier.train()
        tr_loss = []
        for batch in train_loader:
            labels = batch["label"].to(DEVICE)
            optimizer.zero_grad()
            x = m_cls.build_input(batch, fusion, resnet, DEVICE)
            logits = classifier(x)
            loss = criterion(logits, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(all_params, 1.0)
            optimizer.step()
            tr_loss.append(loss.item())

        scheduler.step()
        if (epoch+1) % 10 == 0:
            print(f"    [Epoch {epoch+1}/100] Loss: {np.mean(tr_loss):.4f}")
            
    # ── 3. 가중치 저장 ──────────────────────────────────────────
    print("\n▶ 4. 학습된 모델 가중치(Freeze) 저장 완료")
    torch.save(resnet.state_dict(), os.path.join(MODEL_DIR, "resnet_master.pt"))
    torch.save(fusion.state_dict(), os.path.join(MODEL_DIR, "fusion_master.pt"))
    torch.save(classifier.state_dict(), os.path.join(MODEL_DIR, "classifier_master.pt"))
    
    # ── 4. Youden's J 임계값 추출 ────────────────────────────────
    print("▶ 5. 배포용 Youden's J 임계값 탐색 중...")
    eval_dataset = m_cls.DysarthriaOnlineDataset(train_df, scaler=scaler, is_train=False)
    eval_loader = torch.utils.data.DataLoader(eval_dataset, batch_size=16, shuffle=False)
    
    t_bin, t_sev = evaluate_thresholds_on_train(eval_loader, resnet, fusion, classifier, DEVICE)
    print(f"  [결과] thresh_binary = {t_bin:.4f}, thresh_severe = {t_sev:.4f}")
    
    thresholds = {
        "thresh_binary": t_bin,
        "thresh_severe": t_sev,
        "features": "v1_12_ddk"
    }
    with open(os.path.join(MODEL_DIR, "thresholds.json"), "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=4)
        
    print("\n🎉 Phase 1 마스터 추출 프로세스가 완벽하게 끝났습니다!")
    print(f"확인 경로: {MODEL_DIR}")

if __name__ == "__main__":
    main()

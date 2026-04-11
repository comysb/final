import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score, cohen_kappa_score
import warnings
warnings.filterwarnings("ignore")

import importlib.util

# 1. 05-1 모듈 임포트
DATA_DIR = r"D:\모델1"
def _load_module(name, filename):
    path = os.path.join(DATA_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

m_enc = _load_module("m_enc", "03_deep_encoders.py")
m_fus = _load_module("m_fus", "04_attention_fusion.py")
m_cls = _load_module("m_cls", "05-1_train_classifier.py")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def compute_inv_freq_weights(labels, num_classes=3):
    counts = np.bincount(labels, minlength=num_classes).astype(np.float32)
    counts = np.maximum(counts, 1)
    weights = 1.0 / counts
    weights = weights / weights.sum() * num_classes  # Normalize
    return torch.FloatTensor(weights).to(DEVICE)

def evaluate_fold_youden(test_loader, resnet, fusion, classifier, device):
    """
    2단계 Youden's J 평가:
      Step 1) 정상 vs 비정상 → 이진 Youden's J로 thresh_binary 도출
      Step 2) 비정상 중 경증 vs 중증 → 중증 전용 Youden's J로 thresh_severe 도출
    """
    resnet.eval()
    fusion.eval()
    classifier.eval()
    all_preds, all_trues, all_probs = [], [], []

    with torch.no_grad():
        for batch in test_loader:
            x = m_cls.build_input(batch, fusion, resnet, device)
            logits = classifier(x)
            probs = torch.softmax(logits, dim=1)
            all_preds.extend(logits.argmax(1).cpu().numpy())
            all_trues.extend(batch["label"].numpy())
            all_probs.extend(probs.cpu().numpy())

    all_probs = np.array(all_probs)
    all_trues = np.array(all_trues)

    # ── Step 1: 정상 vs 비정상 Youden's J ──────────────────────────
    anomaly_probs = all_probs[:, 1] + all_probs[:, 2]
    binary_trues  = np.where(all_trues >= 1, 1, 0)

    try:
        from sklearn.metrics import roc_curve
        fpr, tpr, thresholds = roc_curve(binary_trues, anomaly_probs)
        J = tpr - fpr
        thresh_binary = float(thresholds[np.argmax(J)])
    except Exception:
        thresh_binary = 0.5

    # ── Step 2: 중증 전용 Youden's J (비정상 중 중증 여부) ──────────
    # 중증일 확률을 P(severe) / (P(mild)+P(severe)) 로 정규화
    severe_ratio = np.where(
        (all_probs[:, 1] + all_probs[:, 2]) > 0,
        all_probs[:, 2] / (all_probs[:, 1] + all_probs[:, 2] + 1e-8),
        0.0
    )
    severe_trues = np.where(all_trues == 2, 1, 0)

    try:
        fpr_s, tpr_s, thr_s = roc_curve(severe_trues, severe_ratio)
        J_s = tpr_s - fpr_s
        thresh_severe = float(thr_s[np.argmax(J_s)])
    except Exception:
        thresh_severe = 0.5

    # ── 최종 판정: 두 임계값 순차 적용 ─────────────────────────────
    final_preds = []
    for i in range(len(all_trues)):
        if anomaly_probs[i] < thresh_binary:
            final_preds.append(0)          # 정상
        else:
            if severe_ratio[i] >= thresh_severe:
                final_preds.append(2)      # 중증
            else:
                final_preds.append(1)      # 경증

    all_preds = np.array(final_preds)

    micro_acc = accuracy_score(all_trues, all_preds)
    cm = confusion_matrix(all_trues, all_preds, labels=[0, 1, 2])
    with np.errstate(divide='ignore', invalid='ignore'):
        per_class_acc = np.nan_to_num(cm.diagonal() / cm.sum(axis=1))
    macro_acc = np.mean(per_class_acc)

    sensitivities, specificities = [], []
    for i in range(3):
        tp = cm[i, i]
        fn = np.sum(cm[i, :]) - tp
        fp = np.sum(cm[:, i]) - tp
        tn = np.sum(cm) - (tp + fp + fn)
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        sensitivities.append(sens)
        specificities.append(spec)

    sensitivity = float(np.mean(sensitivities))
    specificity = float(np.mean(specificities))

    try:
        roc_auc_multi  = float(roc_auc_score(all_trues, all_probs, multi_class="ovr"))
        roc_auc_binary = float(roc_auc_score(binary_trues, anomaly_probs))
    except Exception:
        roc_auc_multi, roc_auc_binary = 0.0, 0.0

    kappa = float(cohen_kappa_score(all_trues, all_preds))

    return {
        "thresh_binary": thresh_binary,
        "thresh_severe": thresh_severe,
        "micro_acc":     micro_acc,
        "macro_acc":     macro_acc,
        "sensitivity":   sensitivity,
        "specificity":   specificity,
        "sensitivities_per_class": sensitivities,
        "roc_auc_multi": roc_auc_multi,
        "roc_auc_binary":roc_auc_binary,
        "kappa":         kappa,
        "cm":            cm,
    }

def main():
    print("=" * 60)
    print("  중증 민감도 극대화 5-Fold 실험 (Method 1: Weighted CE)")
    print("=" * 60)
    
    df_all_path = os.path.join(DATA_DIR, "features_emb_all.csv")
    aug_pool_path = os.path.join(DATA_DIR, "features_emb_aug_pool.csv")
    
    df_all = pd.read_csv(df_all_path)
    if "uid" not in df_all.columns:
        df_all["uid"] = df_all["path"].apply(lambda x: os.path.basename(x).replace(".wav", ""))

    df_aug = pd.read_csv(aug_pool_path)
    
    base_labels = df_all["label"].values
    print(f"[전체 데이터] 정상: {(base_labels==0).sum()}명, 경증: {(base_labels==1).sum()}명, 중증: {(base_labels==2).sum()}명")
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    all_metrics = []
    total_cm = np.zeros((3, 3), dtype=int)
    
    for fold, (train_idx, test_idx) in enumerate(skf.split(df_all, df_all["label"])):
        print(f"\n▶ Fold {fold+1}/5 시작")
        train_df = df_all.iloc[train_idx].copy()
        test_df = df_all.iloc[test_idx].copy()
        
        severe_uids = train_df[train_df["label"] == 2]["uid"].tolist()
        matched_augs = df_aug[df_aug["original_uid"].isin(severe_uids)]
        
        train_df = pd.concat([train_df, matched_augs], ignore_index=True)
        # NaN 처리 (gender 등 누락된 컬럼 대비)
        train_df = train_df.fillna(0)
        train_df = train_df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        v_counts = train_df["label"].value_counts().sort_index()
        print(f"  - Train 분포: {v_counts.to_dict()} | Test 분포: {test_df['label'].value_counts().sort_index().to_dict()}")
        
        resnet = m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)
        w2v_dim = sum(1 for c in train_df.columns if c.startswith("w2v_")) or 256
        fusion = m_fus.FeatureFusion(ddk_dim=12, w2v_dim=w2v_dim, mel_dim=256, fusion_dim=256).to(DEVICE)
        classifier = m_cls.DysarthriaMLPClassifier(input_dim=fusion.total_dim, num_classes=3).to(DEVICE)
        
        train_dataset = m_cls.DysarthriaOnlineDataset(train_df, fit_scaler=True, is_train=True)
        scaler = train_dataset.scaler
        test_dataset = m_cls.DysarthriaOnlineDataset(test_df, scaler=scaler, is_train=False)
        
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=16, shuffle=True)
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=16, shuffle=False)
        
        # ── Fold별 클래스 가중치 재계산 (train_df 기준)
        fold_labels = train_df["label"].values.astype(int)
        class_weights = compute_inv_freq_weights(fold_labels)
        print(f"  - [가중치] 정상: {class_weights[0]:.2f}, 경증: {class_weights[1]:.2f}, 중증: {class_weights[2]:.2f}")

        optimizer = torch.optim.AdamW(
            list(resnet.parameters()) + list(fusion.parameters()) + list(classifier.parameters()),
            lr=3e-5, weight_decay=1e-4
        )
        from torch.optim.lr_scheduler import CosineAnnealingLR
        scheduler = CosineAnnealingLR(optimizer, T_max=100)
        criterion = nn.CrossEntropyLoss(weight=class_weights)
        all_params = list(resnet.parameters()) + list(fusion.parameters()) + list(classifier.parameters())
        
        # 100 Epochs Train
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
                nn.utils.clip_grad_norm_(all_params, 1.0)  # gradient clipping
                optimizer.step()
                tr_loss.append(loss.item())

            scheduler.step()  # CosineAnnealing 업데이트

            if (epoch+1) % 50 == 0:
                print(f"    [Epoch {epoch+1}/100] Loss: {np.mean(tr_loss):.4f}")
                
        metrics = evaluate_fold_youden(test_loader, resnet, fusion, classifier, DEVICE)
        all_metrics.append(metrics)
        total_cm += metrics["cm"]
        s_cls = metrics["sensitivities_per_class"]
        print(f"  - Fold {fold+1} 결과: Macro Sens: {metrics['sensitivity']*100:.1f}%  "
              f"[정상:{s_cls[0]*100:.0f}% 경증:{s_cls[1]*100:.0f}% 중증:{s_cls[2]*100:.0f}%]  "
              f"Spec: {metrics['specificity']*100:.1f}%  "
              f"thresh_binary={metrics['thresh_binary']:.3f}  thresh_severe={metrics['thresh_severe']:.3f}")

    print("\n" + "="*60)
    print("  🌟 5-Fold 최종 검증 결과 (Method 2: 2단계 Youden's J)")
    print("="*60)
    print(f"  - 평균 Micro Accuracy : {np.mean([m['micro_acc'] for m in all_metrics])*100:.2f}%")
    print(f"  - 평균 Macro Accuracy : {np.mean([m['macro_acc'] for m in all_metrics])*100:.2f}%")
    print(f"  - 평균 Sensitivity    : {np.mean([m['sensitivity'] for m in all_metrics])*100:.2f}%")
    avg_per_class = np.mean([m['sensitivities_per_class'] for m in all_metrics], axis=0)
    print(f"    └ 클래스별: 정상={avg_per_class[0]*100:.1f}%  경증={avg_per_class[1]*100:.1f}%  중증={avg_per_class[2]*100:.1f}%")
    print(f"  - 평균 Specificity    : {np.mean([m['specificity'] for m in all_metrics])*100:.2f}%")
    print(f"  - 평균 ROC-AUC (OVR)  : {np.mean([m['roc_auc_multi'] for m in all_metrics]):.4f}")
    print(f"  - 평균 Cohen's Kappa  : {np.mean([m['kappa'] for m in all_metrics]):.4f}")
    print("  - 누적 총합 Confusion Matrix:\n", total_cm)

if __name__ == "__main__":
    main()

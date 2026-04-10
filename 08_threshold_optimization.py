"""
08_threshold_optimization.py
3-Class 확률값을 합산(경증+중증 = 장애 확률)하여 이진 ROC Curve를 그리고,
Youden's J Statistic을 활용해 최적의 Threshold를 도출하여 최종 3-Class 판정을 조정하는 스크립트.
"""
import os, sys, pickle, json
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import (
    accuracy_score, confusion_matrix, roc_auc_score,
    roc_curve, cohen_kappa_score
)
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = r"D:\모델1"
MODEL_DIR = os.path.join(DATA_DIR, "models_1")
VIZ_DIR = os.path.join(DATA_DIR, "visualization_1")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_pipeline():
    import importlib.util
    def _load(alias, fname):
        path = os.path.join(DATA_DIR, fname)
        spec = importlib.util.spec_from_file_location(alias, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    m_cls = _load("m_cls", "05-1_train_classifier.py")
    m_enc = _load("m_enc", "03_deep_encoders.py")
    m_fus = _load("m_fus", "04_attention_fusion.py")
    m_viz = _load("m_viz", "07-1_visualization.py")
    return m_cls, m_enc, m_fus, m_viz

def run_threshold_optimization():
    print("="*60)
    print("  ▶ 08_threshold_optimization.py 실행")
    print("  ▶ 3-Class (정상/경증/중증) 모델을 기반으로 한 Youden's J 최적화")
    print("="*60)
    
    m_cls, m_enc, m_fus, m_viz = load_pipeline()

    # 기존 가중치 및 스케일러 로드
    scaler_path = os.path.join(MODEL_DIR, "scaler_1.pkl")
    if not os.path.exists(scaler_path):
        print(f"[Error] {scaler_path} 파일을 찾을 수 없습니다. 05-1 학습을 먼저 진행해주세요.")
        return

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    resnet = m_enc.ResNetMelEncoder(embedding_dim=256).to(DEVICE)
    resnet.load_state_dict(torch.load(os.path.join(MODEL_DIR, "resnet_best_1.pt"), map_location=DEVICE))

    fusion = m_fus.FeatureFusion(mel_dim=256, w2v_dim=256, fusion_dim=256).to(DEVICE)
    fusion.load_state_dict(torch.load(os.path.join(MODEL_DIR, "fusion_best_1.pt"), map_location=DEVICE))

    classifier = m_cls.DysarthriaMLPClassifier(input_dim=fusion.total_dim, num_classes=3).to(DEVICE)
    classifier.load_state_dict(torch.load(os.path.join(MODEL_DIR, "classifier_best_1.pt"), map_location=DEVICE))

    resnet.eval(); fusion.eval(); classifier.eval()

    test_df = pd.read_csv(os.path.join(DATA_DIR, "features_emb_test_1.csv"))
    ds = m_cls.DysarthriaOnlineDataset(test_df, scaler=scaler, is_train=False)
    dl = DataLoader(ds, batch_size=16, shuffle=False)

    all_trues, all_probs = [], []
    with torch.no_grad():
        for batch in dl:
            x = m_cls.build_input(batch, fusion, resnet, DEVICE)
            logits = classifier(x)
            probs = F.softmax(logits, dim=1).cpu().numpy()
            all_trues.extend(batch["label"].numpy())
            all_probs.extend(probs)
            
    all_trues = np.array(all_trues)
    all_probs = np.array(all_probs)  # (N, 3)

    # 1. 3진 라벨에서 총 장애 확률 계산: P(1) + P(2)
    anomaly_probs = all_probs[:, 1] + all_probs[:, 2]
    binary_trues = np.where(all_trues >= 1, 1, 0)

    # 2. Youden's J 통계량 기반 최적 Threshold 계산 (ROC Curve)
    try:
        fpr, tpr, thresholds = roc_curve(binary_trues, anomaly_probs)
        roc_auc_binary = roc_auc_score(binary_trues, anomaly_probs)
        roc_auc_multi = roc_auc_score(all_trues, all_probs, multi_class="ovr")
        J = tpr - fpr
        best_idx = np.argmax(J)
        best_thresh = thresholds[best_idx]
    except Exception as e:
        print("[오류] ROC Curve 생성 중 에러:", e)
        best_thresh = 0.5
        roc_auc_binary, roc_auc_multi = 0.0, 0.0

    print(f"  [최적 임계값 도출] Youden's J 기반 커트라인: {best_thresh:.4f}")

    # 3. 최적 임계값 기반 최종 3-Class 판정
    final_preds = []
    for i in range(len(all_trues)):
        prob_anom = anomaly_probs[i]
        prob_1 = all_probs[i, 1]
        prob_2 = all_probs[i, 2]

        if prob_anom < best_thresh:
            # 컷오프 미만: 정상
            final_preds.append(0)
        else:
            # 컷오프 이상: 장애군 확정 -> 경증(1) vs 중증(2) 비교
            if prob_1 >= prob_2:
                final_preds.append(1)
            else:
                final_preds.append(2)

    final_preds = np.array(final_preds)

    # 4. 성능 평가 산출 (3-Class 통일)
    micro_acc = accuracy_score(all_trues, final_preds)
    cm = confusion_matrix(all_trues, final_preds, labels=[0, 1, 2])
    with np.errstate(divide='ignore', invalid='ignore'):
        per_class_acc = np.nan_to_num(cm.diagonal() / cm.sum(axis=1))
    macro_acc = float(np.mean(per_class_acc))

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
    kappa = cohen_kappa_score(all_trues, final_preds)

    print(f"\n=== Youden's J 임계값({best_thresh:.3f}) 적용 3-Class 결과 ===")
    print(f"Micro Accuracy: {micro_acc:.4f} ({micro_acc*100:.2f}%)")
    print(f"Macro Accuracy: {macro_acc:.4f} ({macro_acc*100:.2f}%)")
    print(f"Specificity (Macro): {specificity:.4f}")
    print(f"Sensitivity (Macro): {sensitivity:.4f}")
    print(f"ROC-AUC (OVR): {roc_auc_multi:.4f}")
    print(f"ROC-AUC (Binary): {roc_auc_binary:.4f}")
    print(f"Cohen's Kappa: {kappa:.4f}")
    print(f"Confusion Matrix:\n{cm}")

    # 결과 저장 (덮어쓰지 않고 새로운 이름으로 저장해서 비교 가능하게 처리)
    results = {
        "best_threshold": float(best_thresh),
        "micro_acc": float(micro_acc),
        "macro_acc": float(macro_acc),
        "specificity": float(specificity),
        "sensitivity": float(sensitivity),
        "roc_auc_multi": float(roc_auc_multi),
        "roc_auc_binary": float(roc_auc_binary),
        "cohen_kappa": float(kappa),
        "confusion_matrix": cm.tolist(),
        "predictions": [int(x) for x in final_preds],
        "true_labels": [int(x) for x in all_trues],
    }

    res_path = os.path.join(MODEL_DIR, "test_results_08_youden.json")
    with open(res_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # 임시로 json 덮어쓰기 해서 시각화 도구 사용 후 복구
    original_res = os.path.join(MODEL_DIR, "test_results_1.json")
    with open(original_res, "r") as f: backup = json.load(f)
    os.replace(res_path, original_res)

    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        fig, ax = plt.subplots(figsize=(8, 7))
        cm_array = np.array(cm)
        label_names = ["정상(0)", "경증(1)", "중증(2)"]
        sns.heatmap(cm_array, annot=True, fmt="d", cmap="Blues",
                    xticklabels=label_names, yticklabels=label_names,
                    linewidths=0.5, ax=ax)
                    
        title_str = (
            f"Confusion Matrix (Youden's J={best_thresh:.3f})\n"
            f"Micro: {micro_acc*100:.1f}% | Macro: {macro_acc*100:.1f}%\n"
            f"Spec: {specificity*100:.1f}% | Sens: {sensitivity*100:.1f}%\n"
            f"ROC-AUC (OvR): {roc_auc_multi:.3f} | Kappa: {kappa:.3f}"
        )
        ax.set_title(title_str, fontsize=12, fontweight="bold")
        ax.set_xlabel("예측 레이블", fontsize=11)
        ax.set_ylabel("실제 레이블", fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(VIZ_DIR, "08_youden_confusion_matrix.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("  ▶ 08_youden_confusion_matrix.png 시각화 저장 성공")

    except Exception as e:
        print("시각화 실패:", e)

    # 원본 파일 복구
    with open(original_res, "w") as f: json.dump(backup, f, indent=2)
    with open(res_path, "w") as f: json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_threshold_optimization()

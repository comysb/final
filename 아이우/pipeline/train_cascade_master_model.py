"""
train_cascade_master_model.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
15D Cascade-SVM 최종 마스터 모델 — 100% 훈련 + 직렬화

아키텍처:
  [Base Layer — 6종 × 15 차원 확률벡터]
    ch  1- 3 : 3클래스 SVM + QoV FS
    ch  4- 6 : 3클래스 SVM + RelieFF FS
    ch  7- 9 : 3클래스 SVM + LASSO FS
    ch 10-11 : 정상↔경증 이진 SVM (y≤1 훈련)
    ch 12-13 : 정상(0) vs 비정상(1+2) Cascade SVM
    ch 14-15 : 경증(0) vs 중증(1) Cascade SVM (y≥1 훈련)
  [Meta Layer]
    SVM(RBF, C=10, class_weight={2:5}) + Youden-J 임계값

저장: models/master_model_cascade_15d.pkl
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import os, sys, time, warnings, joblib
import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import f_classif
from sklearn.base import clone
from sklearn.metrics import confusion_matrix

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *
from pipeline.classifier import fs_qov_local, fs_relieff_local, fs_lasso_local, compute_metrics
from pipeline.feature_selection import get_initial_topN, backward_stepwise_selection

# ── 경로 ─────────────────────────────────────────────────────────────────────
HYBRID_AUG_FEATURES_CSV = os.path.join(RESULTS_DIR, "features_hybrid_augmented_v2.csv")
MODELS_DIR        = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
OOF_PROBS_NPY     = os.path.join(RESULTS_DIR, "oof_probs_15d_cascade_no_w2v.npy")
OOF_MASK_NPY      = os.path.join(RESULTS_DIR, "oof_mask_15d_cascade_no_w2v.npy")
CASCADE_MASTER_PKL = os.path.join(MODELS_DIR, "master_model_cascade_15d.pkl")
os.makedirs(MODELS_DIR, exist_ok=True)

BASE_SVM = SVC(
    kernel="rbf", C=1.0, gamma="scale",
    class_weight="balanced", probability=True, random_state=42
)


# ─────────────────────────────────────────────────────────────────────────────
def _preprocess_full(X_all, y_all):
    """100% 데이터 기반 공통 전처리: Impute → Scale → ANOVA 필터."""
    imp    = SimpleImputer(strategy="median")
    X_imp  = imp.fit_transform(X_all)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X_imp)

    _, p   = f_classif(X_sc, y_all)
    sig_idx = np.where(p < 0.05)[0]
    if   len(sig_idx) < 30:  sig_idx = np.argsort(p)[:50]
    elif len(sig_idx) > 300: sig_idx = np.argsort(p)[:300]

    return imp, scaler, X_sc, sig_idx


def _fit_base_svm(X_sc_sub, y_sub, sig_idx, fs_name, label):
    """
    지정 데이터(서브셋 가능)로 BSS → 100% fit.
    X_sc_sub : 이미 scale된 배열 (훈련 대상 행만)
    y_sub    : 레이블 (이진 또는 3클래스)
    """
    X_sig = X_sc_sub[:, sig_idx]

    if   fs_name == "QoV":    ranking = fs_qov_local(X_sig, y_sub)
    elif fs_name == "RelieFF": ranking = fs_relieff_local(X_sig, y_sub, k=10)
    else:                      ranking = fs_lasso_local(X_sig, y_sub)

    # BSS용 20% 임시 검증 분리
    np.random.seed(42)
    shuf    = np.random.permutation(len(y_sub))
    val_n   = max(1, int(len(y_sub) * 0.2))
    tr_idx  = shuf[val_n:]
    val_idx = shuf[:val_n]

    _, top_n = get_initial_topN(
        ranking, X_sig[tr_idx], y_sub[tr_idx],
        clone(BASE_SVM), N_max=min(30, len(ranking))
    )
    best_subset, _ = backward_stepwise_selection(
        X_sig[tr_idx],  y_sub[tr_idx],
        X_sig[val_idx], y_sub[val_idx],
        top_n, clone(BASE_SVM), verbose=False
    )
    if len(best_subset) == 0:
        best_subset = top_n[:1]

    # 100% 최종 훈련
    clf = clone(BASE_SVM)
    clf.fit(X_sig[:, best_subset], y_sub)
    print(f"    [{label}] BSS 최적 피처 {len(best_subset)}개 → 100% fit 완료")
    return best_subset, clf


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║  👑 15D Cascade-SVM 최종 마스터 모델 — 100% 훈련 + 직렬화                  ║")
    print("║  🔴 W2V 완전 제거 — Praat 임상 피처(112차원)만 사용                         ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝\n")
    start = time.time()

    # ── 1. 데이터 로드 ───────────────────────────────────────────────────────
    print(">> [Step 1] 데이터 로드")
    df = pd.read_csv(HYBRID_AUG_FEATURES_CSV, encoding="utf-8-sig")
    df = df.dropna(subset=["장애정도"])

    meta_cols = ["UID", "speaker_id", "장애정도", "augmented", "aug_type"]
    feat_cols = [c for c in df.columns
                 if c not in meta_cols and not str(c).startswith("W2V_")]
    print(f"   피처: {len(feat_cols)}개 | 세션: {len(df)}개")

    X_all       = df[feat_cols].values.astype(float)
    y_all       = df["장애정도"].values.astype(int)
    aug_flags   = df["augmented"].values.astype(int)

    # ── 2. 공통 전처리 (100% fit) ────────────────────────────────────────────
    print("\n>> [Step 2] 공통 전처리기 100% Fit (Impute / Scale / ANOVA)")
    imp, scaler, X_sc, sig_idx = _preprocess_full(X_all, y_all)
    print(f"   ANOVA 통과 피처: {len(sig_idx)}개")

    # ── 3. Base SVM 6종 — 100% 훈련 ─────────────────────────────────────────
    print("\n>> [Step 3] Base SVM 6종 100% 훈련")
    base_models = []

    # ch 1-3: 3클래스 QoV SVM
    print("  [ch 1-3] 3클래스 QoV SVM")
    bs, clf = _fit_base_svm(X_sc, y_all, sig_idx, "QoV", "3cls_QoV")
    base_models.append({"name": "3cls_QoV",     "best_subset": bs, "clf": clf,
                        "mode": "3class",        "n_out": 3})

    # ch 4-6: 3클래스 RelieFF SVM
    print("  [ch 4-6] 3클래스 RelieFF SVM")
    bs, clf = _fit_base_svm(X_sc, y_all, sig_idx, "RelieFF", "3cls_RelieFF")
    base_models.append({"name": "3cls_RelieFF", "best_subset": bs, "clf": clf,
                        "mode": "3class",        "n_out": 3})

    # ch 7-9: 3클래스 LASSO SVM
    print("  [ch 7-9] 3클래스 LASSO SVM")
    bs, clf = _fit_base_svm(X_sc, y_all, sig_idx, "LASSO", "3cls_LASSO")
    base_models.append({"name": "3cls_LASSO",   "best_subset": bs, "clf": clf,
                        "mode": "3class",        "n_out": 3})

    # ch 10-11: 정상↔경증 이진 SVM (y≤1 훈련)
    print("  [ch 10-11] 정상↔경증 이진 SVM (y≤1 훈련 / 전체 추론)")
    nm_mask   = y_all <= 1
    bs, clf   = _fit_base_svm(X_sc[nm_mask], y_all[nm_mask], sig_idx, "LASSO", "bin_nm")
    base_models.append({"name": "bin_nm",       "best_subset": bs, "clf": clf,
                        "mode": "binary",        "n_out": 2})

    # ch 12-13: 정상(0) vs 비정상(1+2) Cascade SVM
    print("  [ch 12-13] 정상 vs 비정상 Cascade SVM (전체 훈련)")
    y_cas1  = (y_all >= 1).astype(int)
    bs, clf = _fit_base_svm(X_sc, y_cas1, sig_idx, "LASSO", "cascade_norm")
    base_models.append({"name": "cascade_norm", "best_subset": bs, "clf": clf,
                        "mode": "binary",        "n_out": 2})

    # ch 14-15: 경증(0) vs 중증(1) Cascade SVM (y≥1 훈련)
    print("  [ch 14-15] 경증 vs 중증 Cascade SVM (y≥1 훈련 / 전체 추론)")
    ms_mask   = y_all >= 1
    y_ms_bin  = (y_all[ms_mask] == 2).astype(int)
    bs, clf   = _fit_base_svm(X_sc[ms_mask], y_ms_bin, sig_idx, "LASSO", "cascade_sev")
    base_models.append({"name": "cascade_sev",  "best_subset": bs, "clf": clf,
                        "mode": "binary",        "n_out": 2})

    # ── 4. OOF 15D 벡터 로드 (캐시 우선) ────────────────────────────────────
    print("\n>> [Step 4] 15D OOF 메타 피처 확보")
    if os.path.exists(OOF_PROBS_NPY) and os.path.exists(OOF_MASK_NPY):
        print("   캐시된 OOF 행렬 로드 중... (oof_probs_15d_cascade_no_w2v.npy)")
        oof_probs = np.load(OOF_PROBS_NPY)
        oof_mask  = np.load(OOF_MASK_NPY)
        # 원본 데이터(증강 제외)만 사용
        clean_mask = (aug_flags == 0)
        oof_mask   = oof_mask & clean_mask
        print(f"   OOF 유효 샘플: {oof_mask.sum()}개 (원본 세션, 증강 제외)")
    else:
        raise FileNotFoundError(
            "OOF 캐시가 없습니다. run_cv_hybrid_stacking_cascade_svm.py 를 먼저 실행하세요."
        )

    # ── 5. 메타 학습기 훈련 ──────────────────────────────────────────────────
    print("\n>> [Step 5] SVM 메타 학습기 훈련 (15D → 3클래스)")
    X_meta    = oof_probs[oof_mask]           # (n_clean, 15)
    y_meta    = y_all[oof_mask]

    meta_scaler  = StandardScaler()
    X_meta_sc    = meta_scaler.fit_transform(X_meta)

    meta_clf = SVC(
        kernel="rbf", C=10.0, gamma="scale",
        class_weight={0: 1.0, 1: 1.0, 2: 5.0},
        probability=True, random_state=42
    )
    meta_clf.fit(X_meta_sc, y_meta)
    meta_probs = meta_clf.predict_proba(X_meta_sc)
    print(f"   메타 학습기 훈련 완료 (n={len(y_meta)})")

    # ── 6. Youden-J 최적 임계값 탐색 ─────────────────────────────────────────
    print("\n>> [Step 6] Youden-J 임계값 탐색 (중증 Sens ≥ 50%)")
    y_bin_sev = (y_meta == 2).astype(int)
    best_j, best_th, best_m = -np.inf, 0.5, None

    for th in np.arange(0.01, 1.00, 0.01):
        preds = np.argmax(meta_probs, axis=1).copy()
        preds[meta_probs[:, 2] >= th] = 2
        m = compute_metrics(y_meta, preds, meta_probs)

        TP  = np.sum((meta_probs[:,2] >= th) & (y_bin_sev == 1))
        FN  = np.sum((meta_probs[:,2] <  th) & (y_bin_sev == 1))
        TN  = np.sum((meta_probs[:,2] <  th) & (y_bin_sev == 0))
        FP  = np.sum((meta_probs[:,2] >= th) & (y_bin_sev == 0))
        tpr = TP / (TP + FN) if (TP + FN) > 0 else 0
        tnr = TN / (TN + FP) if (TN + FP) > 0 else 0
        j   = tpr + tnr - 1

        if m["sens_2"] >= 0.50 and j > best_j:
            best_j, best_th, best_m = j, round(th, 3), m

    if best_m is None:          # 50% 보장 안 되면 Youden만 최대화
        for th in np.arange(0.01, 1.00, 0.01):
            preds = np.argmax(meta_probs, axis=1).copy()
            preds[meta_probs[:, 2] >= th] = 2
            m   = compute_metrics(y_meta, preds, meta_probs)
            TP  = np.sum((meta_probs[:,2] >= th) & (y_bin_sev == 1))
            FN  = np.sum((meta_probs[:,2] <  th) & (y_bin_sev == 1))
            TN  = np.sum((meta_probs[:,2] <  th) & (y_bin_sev == 0))
            FP  = np.sum((meta_probs[:,2] >= th) & (y_bin_sev == 0))
            tpr = TP / (TP + FN) if (TP + FN) > 0 else 0
            tnr = TN / (TN + FP) if (TN + FP) > 0 else 0
            j   = tpr + tnr - 1
            if j > best_j:
                best_j, best_th, best_m = j, round(th, 3), m

    best_preds = np.argmax(meta_probs, axis=1).copy()
    best_preds[meta_probs[:, 2] >= best_th] = 2
    cm = confusion_matrix(y_meta, best_preds, labels=[0, 1, 2])

    print(f"\n   최적 임계값: {best_th:.3f}  (Youden J={best_j:.3f})")
    print(f"   Micro Acc: {best_m['micro_acc']*100:.1f}% | "
          f"정상: {best_m['sens_0']*100:.1f}% | "
          f"경증: {best_m['sens_1']*100:.1f}% | "
          f"중증: {best_m['sens_2']*100:.1f}%")
    print(f"\n   [ 혼동 행렬 (Threshold={best_th:.3f}) ]")
    print(f"          예측_정상  예측_경증  예측_중증")
    print(f"   실제_정상  {cm[0,0]:4d}     {cm[0,1]:4d}     {cm[0,2]:4d}")
    print(f"   실제_경증  {cm[1,0]:4d}     {cm[1,1]:4d}     {cm[1,2]:4d}")
    print(f"   실제_중증  {cm[2,0]:4d}     {cm[2,1]:4d}     {cm[2,2]:4d}")

    # ── 7. 직렬화 ─────────────────────────────────────────────────────────────
    print(f"\n>> [Step 7] Cascade 마스터 모델 저장")
    cascade_master = {
        "model_name":      "15D_Cascade_SVM_W2V_Free",
        "feature_names":   feat_cols,          # 112개 Praat 피처명 (순서 보장)
        "imputer":         imp,                 # 공통 결측치 처리기
        "scaler":          scaler,              # 공통 정규화
        "sig_idx":         sig_idx,             # ANOVA 통과 인덱스
        "base_models":     base_models,         # 6종 Base SVM (ch 1~15)
        "meta_scaler":     meta_scaler,         # 메타 피처 스케일러
        "meta_classifier": meta_clf,            # 메타 SVM
        "best_threshold":  best_th,             # Youden-J 최적 임계값
        "performance": {
            "micro_acc": round(best_m["micro_acc"] * 100, 1),
            "sens_정상": round(best_m["sens_0"]    * 100, 1),
            "sens_경증": round(best_m["sens_1"]    * 100, 1),
            "sens_중증": round(best_m["sens_2"]    * 100, 1),
            "roc_auc":   round(best_m["roc_auc"],   3),
            "youden_j":  round(best_j, 3),
            "threshold": best_th,
        }
    }
    joblib.dump(cascade_master, CASCADE_MASTER_PKL)
    sz = os.path.getsize(CASCADE_MASTER_PKL) // 1024
    print(f"   ✅ 저장 완료: {CASCADE_MASTER_PKL} ({sz}KB)")

    print(f"\n{'='*85}")
    print(f"🚀 15D Cascade 마스터 모델 직렬화 완료! (총 {time.time()-start:.1f}초)")
    print(f"{'='*85}")


if __name__ == "__main__":
    main()

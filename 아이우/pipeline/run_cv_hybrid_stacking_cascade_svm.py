"""
[ Phase 9 ] 15차원 계단식(Cascade) + SVM 메타 학습기 하이브리드 스태킹
- 기존 11D (3클래스 SVM x 3 + 이진 정상/경증 전문가 x 1)
- 신규 추가 채널 2종:
    ch 12-13: 정상(0) vs 비정상(1+2) 전용 SVM  → 정상 재현율 극대화
    ch 14-15: 경증(1) vs 중증(2) 전용 SVM        → 경증/중증 정밀 구분
- 메타 학습기: LogisticRegression → SVC(RBF) 교체
"""
import os, sys, time, warnings
import pandas as pd
import numpy as np
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.base import clone
from sklearn.feature_selection import f_classif
from sklearn.metrics import confusion_matrix

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *
from pipeline.classifier import compute_metrics
from pipeline.classifier import fs_qov_local, fs_relieff_local, fs_lasso_local
from pipeline.feature_selection import get_initial_topN, backward_stepwise_selection

# ──────────────────── 경로 설정 ────────────────────
HYBRID_AUG_FEATURES_CSV = os.path.join(RESULTS_DIR, "features_hybrid_augmented_v2.csv")
RESULTS_CSV = os.path.join(RESULTS_DIR, "final_results_cascade_svm_meta_no_w2v.csv")
OOF_PROBS_NPY = os.path.join(RESULTS_DIR, "oof_probs_15d_cascade_no_w2v.npy")
OOF_MASK_NPY  = os.path.join(RESULTS_DIR, "oof_mask_15d_cascade_no_w2v.npy")

# ──────────────────── 공통 베이스 SVM ────────────────────
BASE_SVM = SVC(kernel="rbf", C=1.0, gamma="scale",
               class_weight="balanced", probability=True, random_state=42)


def _preprocess(X_tr_raw, y_tr, X_te_raw, for_labels=None):
    """
    공통 전처리: Impute → Scale → ANOVA 필터.
    for_labels: None이면 y_tr 전체 사용, 그렇지 않으면 해당 레이블만 train 데이터 마스킹.
    반환: X_tr_sig, X_te_sig (ANOVA 필터 후)
    """
    imp = SimpleImputer(strategy="median")
    X_tr = imp.fit_transform(X_tr_raw)
    X_te = imp.transform(X_te_raw)

    scaler = StandardScaler()
    X_tr_sc = scaler.fit_transform(X_tr)
    X_te_sc = scaler.transform(X_te)

    # ANOVA 필터: 전체 train 기준(레이블 필터링 전)
    F_tr, p_tr = f_classif(X_tr_sc, y_tr)
    sig_idx = np.where(p_tr < 0.05)[0]
    if len(sig_idx) < 30:
        sig_idx = np.argsort(p_tr)[:50]
    elif len(sig_idx) > 300:
        sig_idx = np.argsort(p_tr)[:300]

    return X_tr_sc, X_te_sc, sig_idx


def _fit_predict_binary(X_tr_sc, y_tr_bin, X_te_sc, sig_idx, fs_name, n_classes=2):
    """
    이진 분류기 훈련 및 예측.
    y_tr_bin: 이미 이진화(0/1)된 레이블
    반환: (N_test, n_classes) 확률 배열
    """
    X_tr_sig = X_tr_sc[:, sig_idx]
    X_te_sig = X_te_sc[:, sig_idx]

    if fs_name == "QoV":
        ranking = fs_qov_local(X_tr_sig, y_tr_bin)
    elif fs_name == "RelieFF":
        ranking = fs_relieff_local(X_tr_sig, y_tr_bin, k=10)
    elif fs_name == "LASSO":
        ranking = fs_lasso_local(X_tr_sig, y_tr_bin)
    else:
        ranking = list(range(X_tr_sig.shape[1]))

    val_size = max(1, int(len(y_tr_bin) * 0.2))
    X_bss_tr, X_bss_val = X_tr_sig[:-val_size], X_tr_sig[-val_size:]
    y_bss_tr, y_bss_val = y_tr_bin[:-val_size], y_tr_bin[-val_size:]

    _, top_n_idx = get_initial_topN(
        ranking, X_tr_sig, y_tr_bin,
        clone(BASE_SVM), N_max=min(30, len(ranking))
    )

    best_subset, _ = backward_stepwise_selection(
        X_bss_tr, y_bss_tr, X_bss_val, y_bss_val,
        top_n_idx, clone(BASE_SVM), verbose=False
    )
    if len(best_subset) == 0:
        best_subset = top_n_idx[:1]

    clf = clone(BASE_SVM)
    clf.fit(X_tr_sig[:, best_subset], y_tr_bin)
    return clf.predict_proba(X_te_sig[:, best_subset])   # shape (N_te, 2)


def collect_oof_15d(X_all, y_all, speaker_ids, aug_flags, sgkf):
    """5-Fold 교차검증으로 15차원 OOF 확률 행렬을 수집합니다."""
    print(">> [Stage 1 OOF] 15차원 Cascade OOF 수집 시작... (약 20분 소요)")
    oof_probs = np.zeros((len(X_all), 15))
    oof_mask  = np.zeros(len(X_all), dtype=bool)

    splits = list(sgkf.split(X_all, y_all, groups=speaker_ids))

    for fold_i, (train_idx, test_idx) in enumerate(splits):
        t0 = time.time()
        clean_test_mask = aug_flags[test_idx] == 0
        clean_test_idx  = test_idx[clean_test_mask]

        X_tr_raw = X_all[train_idx]
        X_te_raw = X_all[clean_test_idx]
        y_tr     = y_all[train_idx]

        # 공통 전처리
        X_tr_sc, X_te_sc, sig_idx = _preprocess(X_tr_raw, y_tr, X_te_raw)

        fold_probs = []

        # ── [채널 1~9] 기존 3클래스 전문가 3종 × 3차원 ──────────────
        for fs_name in ["LASSO", "RelieFF", "QoV"]:
            probs = _fit_predict_binary(X_tr_sc, y_tr, X_te_sc, sig_idx, fs_name, n_classes=3)
            # 3클래스 모델: predict_proba 자체가 (N, 3) → 그대로 사용
            # 단, _fit_predict_binary는 이진 전용이므로 별도 처리
            # 3클래스 모델은 y_tr 원본(0/1/2) 레이블로 학습
            X_tr_sig = X_tr_sc[:, sig_idx]
            X_te_sig = X_te_sc[:, sig_idx]

            if fs_name == "QoV":
                ranking = fs_qov_local(X_tr_sig, y_tr)
            elif fs_name == "RelieFF":
                ranking = fs_relieff_local(X_tr_sig, y_tr, k=10)
            else:
                ranking = fs_lasso_local(X_tr_sig, y_tr)

            val_size = max(1, int(len(y_tr) * 0.2))
            _, top_n_idx = get_initial_topN(
                ranking, X_tr_sig, y_tr, clone(BASE_SVM), N_max=min(30, len(ranking))
            )
            best_subset, _ = backward_stepwise_selection(
                X_tr_sig[:-val_size], y_tr[:-val_size],
                X_tr_sig[-val_size:], y_tr[-val_size:],
                top_n_idx, clone(BASE_SVM), verbose=False
            )
            if len(best_subset) == 0:
                best_subset = top_n_idx[:1]

            clf3 = clone(BASE_SVM)
            clf3.fit(X_tr_sig[:, best_subset], y_tr)
            probs3 = clf3.predict_proba(X_te_sig[:, best_subset])  # (N, 3)
            fold_probs.append(probs3)

        # ── [채널 10~11] 기존 정상↔경증 이진 전문가 ─────────────────
        # 학습: 정상(0), 경증(1) 만으로 훈련 / 추론: 전체(중증 포함)
        nm_mask  = y_tr <= 1
        X_tr_nm  = X_tr_sc[nm_mask][:, sig_idx]
        y_tr_nm  = y_tr[nm_mask]          # 0 또는 1
        X_te_nm  = X_te_sc[:, sig_idx]

        if fs_lasso_local is not None:
            ranking_nm = fs_lasso_local(X_tr_nm, y_tr_nm)
        else:
            ranking_nm = list(range(X_tr_nm.shape[1]))

        val_sz = max(1, int(len(y_tr_nm) * 0.2))
        _, top_nm = get_initial_topN(
            ranking_nm, X_tr_nm, y_tr_nm,
            clone(BASE_SVM), N_max=min(30, len(ranking_nm))
        )
        best_nm, _ = backward_stepwise_selection(
            X_tr_nm[:-val_sz], y_tr_nm[:-val_sz],
            X_tr_nm[-val_sz:], y_tr_nm[-val_sz:],
            top_nm, clone(BASE_SVM), verbose=False
        )
        if len(best_nm) == 0:
            best_nm = top_nm[:1]

        clf_nm = clone(BASE_SVM)
        clf_nm.fit(X_tr_nm[:, best_nm], y_tr_nm)
        probs_nm = clf_nm.predict_proba(X_te_nm[:, best_nm])  # (N, 2)
        fold_probs.append(probs_nm)

        # ── [채널 12~13] 🆕 정상(0) vs 비정상(1+2) 계단식 ──────────
        y_tr_cascade1 = (y_tr >= 1).astype(int)  # 0=정상, 1=비정상
        X_tr_sig_all  = X_tr_sc[:, sig_idx]
        X_te_sig_all  = X_te_sc[:, sig_idx]

        ranking_c1 = fs_lasso_local(X_tr_sig_all, y_tr_cascade1)
        val_sz = max(1, int(len(y_tr_cascade1) * 0.2))
        _, top_c1 = get_initial_topN(
            ranking_c1, X_tr_sig_all, y_tr_cascade1,
            clone(BASE_SVM), N_max=min(30, len(ranking_c1))
        )
        best_c1, _ = backward_stepwise_selection(
            X_tr_sig_all[:-val_sz], y_tr_cascade1[:-val_sz],
            X_tr_sig_all[-val_sz:], y_tr_cascade1[-val_sz:],
            top_c1, clone(BASE_SVM), verbose=False
        )
        if len(best_c1) == 0:
            best_c1 = top_c1[:1]

        clf_c1 = clone(BASE_SVM)
        clf_c1.fit(X_tr_sig_all[:, best_c1], y_tr_cascade1)
        probs_c1 = clf_c1.predict_proba(X_te_sig_all[:, best_c1])  # (N, 2): [P(정상), P(비정상)]
        fold_probs.append(probs_c1)

        # ── [채널 14~15] 🆕 경증(1) vs 중증(2) 계단식 ───────────────
        ms_mask       = y_tr >= 1
        X_tr_ms       = X_tr_sc[ms_mask][:, sig_idx]
        y_tr_ms_bin   = (y_tr[ms_mask] == 2).astype(int)  # 0=경증, 1=중증

        if len(np.unique(y_tr_ms_bin)) < 2:
            # 중증이 한 종류뿐인 fold → 더미 확률
            probs_ms = np.zeros((len(clean_test_idx), 2))
            probs_ms[:, 0] = 1.0  # 기본값: 전부 경증 예측
        else:
            ranking_ms = fs_lasso_local(X_tr_ms, y_tr_ms_bin)
            val_sz = max(1, int(len(y_tr_ms_bin) * 0.2))
            _, top_ms = get_initial_topN(
                ranking_ms, X_tr_ms, y_tr_ms_bin,
                clone(BASE_SVM), N_max=min(30, len(ranking_ms))
            )
            best_ms, _ = backward_stepwise_selection(
                X_tr_ms[:-val_sz], y_tr_ms_bin[:-val_sz],
                X_tr_ms[-val_sz:], y_tr_ms_bin[-val_sz:],
                top_ms, clone(BASE_SVM), verbose=False
            )
            if len(best_ms) == 0:
                best_ms = top_ms[:1]

            clf_ms = clone(BASE_SVM)
            clf_ms.fit(X_tr_ms[:, best_ms], y_tr_ms_bin)
            X_te_ms = X_te_sc[:, sig_idx]
            probs_ms = clf_ms.predict_proba(X_te_ms[:, best_ms])  # (N, 2): [P(경증), P(중증)]

        fold_probs.append(probs_ms)

        # ── 결합 ──────────────────────────────────────────────────────
        stacked = np.hstack(fold_probs)   # (N_clean_te, 15)
        oof_probs[clean_test_idx] = stacked
        oof_mask[clean_test_idx]  = True

        print(f"   ▶ Fold {fold_i+1}/5 완료 ({time.time()-t0:.1f}초) | 형상: {stacked.shape}")

    np.save(OOF_PROBS_NPY, oof_probs)
    np.save(OOF_MASK_NPY,  oof_mask)
    print("\n>> [Stage 1 완료] 15차원 OOF 저장 완료!")
    return oof_probs, oof_mask


def main():
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║ 🚀 [ Phase 9 ] 15차원 Cascade + SVM 메타 학습기 하이브리드 스태킹          ║")
    print("║   ch 01-09: 기존 3클래스 SVM×3 전문가                                     ║")
    print("║   ch 10-11: 정상↔경증 이진 전담 SVM                                       ║")
    print("║   ch 12-13: 🆕 정상(0) vs 비정상(1+2) Cascade SVM                         ║")
    print("║   ch 14-15: 🆕 경증(1) vs 중증(2) Cascade SVM                              ║")
    print("║   Meta    : 🔥 SVM(RBF, balanced)                                          ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")

    df = pd.read_csv(HYBRID_AUG_FEATURES_CSV, encoding="utf-8-sig")
    df = df.dropna(subset=['장애정도'])

    meta_cols = ["UID", "speaker_id", "장애정도", "augmented", "aug_type"]
    
    # 🚨 Wav2Vec2 피처 강제 제외 (임상 피처만 사용)
    feat_cols = [c for c in df.columns if c not in meta_cols and not str(c).startswith("W2V_")]
    print(f">> 🔴 사용할 1차 파생 피처 개수: {len(feat_cols)} (Wav2Vec2 강제 제외)\n")

    X_all       = df[feat_cols].values.astype(float)
    y_all       = df["장애정도"].values.astype(int)
    speaker_ids = df["speaker_id"].values.astype(str)
    aug_flags   = df["augmented"].values.astype(int)

    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)

    # ── OOF 수집 (캐시 우선) ──────────────────────────────────────────
    if os.path.exists(OOF_PROBS_NPY) and os.path.exists(OOF_MASK_NPY):
        print(">> [Stage 1 OOF] 캐싱된 15차원 OOF 행렬 로드 중...")
        oof_probs = np.load(OOF_PROBS_NPY)
        oof_mask  = np.load(OOF_MASK_NPY)
    else:
        oof_probs, oof_mask = collect_oof_15d(X_all, y_all, speaker_ids, aug_flags, sgkf)

    # ── [Stage 2] 🔥 SVM 메타 학습기 ────────────────────────────────
    X_meta = oof_probs[oof_mask]
    y_meta = y_all[oof_mask]

    print(f"\n>> [Stage 2 Meta] SVM(RBF) 메타 학습기 훈련 중... (입력: {X_meta.shape})")
    
    # 메타 학습기 자체 내부에서도 스케일링이 필요!
    meta_scaler = StandardScaler()
    X_meta_sc = meta_scaler.fit_transform(X_meta)

    # 중증에 강한 가중치 유지
    meta_clf = SVC(kernel="rbf", C=10.0, gamma="scale",
                   class_weight={0: 1.0, 1: 1.0, 2: 5.0},
                   probability=True, random_state=42)
    meta_clf.fit(X_meta_sc, y_meta)
    meta_probs = meta_clf.predict_proba(X_meta_sc)

    # ── [Stage 3] Youden J + 정확도 최우선 임계값 탐색 ─────────────
    print("\n>> [Stage 3] Youden J 최우선 임계값 스위핑 (중증 50% 보장)")

    y_binary_sev = (y_meta == 2).astype(int)
    sweep_results = []

    for th in np.arange(0.01, 1.00, 0.01):
        prob_sev = meta_probs[:, 2]
        preds = np.argmax(meta_probs, axis=1)
        preds[prob_sev >= th] = 2
        metrics = compute_metrics(y_meta, preds, meta_probs)

        TP = np.sum((prob_sev >= th) & (y_binary_sev == 1))
        FN = np.sum((prob_sev <  th) & (y_binary_sev == 1))
        TN = np.sum((prob_sev <  th) & (y_binary_sev == 0))
        FP = np.sum((prob_sev >= th) & (y_binary_sev == 0))
        tpr = TP / (TP + FN) if (TP + FN) > 0 else 0
        tnr = TN / (TN + FP) if (TN + FP) > 0 else 0
        j = tpr + tnr - 1

        sweep_results.append({
            "Threshold":  round(th, 3),
            "Youden_J":   round(j, 4),
            "Micro_Acc":  metrics['micro_acc'],
            "Sens_정상":  metrics['sens_0'],
            "Sens_경증":  metrics['sens_1'],
            "Sens_중증":  metrics['sens_2']
        })

    df_sweep = pd.DataFrame(sweep_results)

    # 중증 50% 이상 보장 후 Youden J 내림차순
    filtered = df_sweep[df_sweep["Sens_중증"] >= 0.50].sort_values(
        by=["Youden_J", "Micro_Acc"], ascending=[False, False]
    )

    print("\n" + "="*80)
    print("🏆 Top 10 (중증 50% 보장 + Youden J 최우선 | 15D Cascade + SVM 메타)")
    print("="*80)

    top10 = filtered.head(10).copy()
    for col in top10.columns:
        if col not in ["Threshold", "Youden_J"]:
            top10[col] = (top10[col] * 100).apply(lambda x: f"{x:.1f}%")
        else:
            top10[col] = top10[col].apply(lambda x: f"{x:.3f}")
    print(top10.to_string(index=False))
    print("="*80)

    if len(filtered) > 0:
        best_row = filtered.iloc[0]
        best_th  = float(best_row["Threshold"])
        print(f"\n🥇 최우수 임계값: {best_th:.3f}  (Youden J: {float(best_row['Youden_J']):.3f}, "
              f"Micro_Acc: {best_row['Micro_Acc']*100:.1f}%)")

        best_preds = np.argmax(meta_probs, axis=1)
        best_preds[meta_probs[:, 2] >= best_th] = 2
        cm = confusion_matrix(y_meta, best_preds, labels=[0, 1, 2])

        print(f"\n[ 혼돈 행렬 (Threshold {best_th:.3f}) ]")
        print(f"       예측_정상  예측_경증  예측_중증")
        print(f"실제_정상    {cm[0,0]:2d}       {cm[0,1]:2d}       {cm[0,2]:2d}")
        print(f"실제_경증    {cm[1,0]:2d}       {cm[1,1]:2d}       {cm[1,2]:2d}")
        print(f"실제_중증    {cm[2,0]:2d}       {cm[2,1]:2d}       {cm[2,2]:2d}")
        print(f"--------------------------------------")

        # ── 정확도 최우선 세팅도 출력 (참고용) ──────────────────────
        best_acc_row = df_sweep[df_sweep["Sens_중증"] >= 0.50].sort_values(
            by=["Micro_Acc", "Threshold"], ascending=[False, True]
        ).iloc[0]
        best_acc_th = float(best_acc_row["Threshold"])
        print(f"\n📌 [참고] 정확도 최우선 임계값: {best_acc_th:.3f}  "
              f"(Micro_Acc: {best_acc_row['Micro_Acc']*100:.1f}%, "
              f"Sens_경증: {best_acc_row['Sens_경증']*100:.1f}%)")
        best_preds2 = np.argmax(meta_probs, axis=1)
        best_preds2[meta_probs[:, 2] >= best_acc_th] = 2
        cm2 = confusion_matrix(y_meta, best_preds2, labels=[0, 1, 2])
        print(f"       예측_정상  예측_경증  예측_중증")
        print(f"실제_정상    {cm2[0,0]:2d}       {cm2[0,1]:2d}       {cm2[0,2]:2d}")
        print(f"실제_경증    {cm2[1,0]:2d}       {cm2[1,1]:2d}       {cm2[1,2]:2d}")
        print(f"실제_중증    {cm2[2,0]:2d}       {cm2[2,1]:2d}       {cm2[2,2]:2d}")

    df_sweep.to_csv(RESULTS_CSV, index=False, encoding="utf-8-sig")
    print(f"\n결과 저장 완료: {RESULTS_CSV}")


if __name__ == "__main__":
    main()

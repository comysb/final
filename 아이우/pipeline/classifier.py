"""
STEP 8-10: 분류 + StratifiedGroupKFold + 평가 지표
출력: results/final_results.csv
"""
import os, sys, warnings
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix,
    f1_score, roc_auc_score
)

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[WARN] XGBoost 미설치. XGB 분류기 제외.")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *
from pipeline.feature_selection import (
    run_anova_filter, run_feature_selection,
    backward_stepwise_selection, get_initial_topN
)


# ──────────────────────────────────────────────────────────────
# 평가 지표 계산
# ──────────────────────────────────────────────────────────────

def compute_metrics(y_true, y_pred, y_prob):
    """
    전체 평가 지표 계산.

    Returns
    -------
    dict with:
      micro_acc   : 전체 accuracy (= macro micro accuracy)
      macro_acc   : 클래스별 accuracy 평균
      sens_0/1/2  : 클래스별 sensitivity (정상/경증/중증)
      avg_sens    : sensitivity 평균
      avg_spec    : specificity 평균
      roc_auc     : multi-class OvR macro AUC
    """
    # ── Micro Accuracy (= 전체 정확도)
    micro_acc = accuracy_score(y_true, y_pred)

    # ── Confusion Matrix → per-class 지표
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    n_cls = cm.shape[0]

    sens_list = []
    spec_list = []
    class_acc_list = []

    for i in range(n_cls):
        TP = cm[i, i]
        FN = cm[i, :].sum() - TP
        FP = cm[:, i].sum() - TP
        TN = cm.sum() - TP - FN - FP

        sens = TP / (TP + FN) if (TP + FN) > 0 else 0.0
        spec = TN / (TN + FP) if (TN + FP) > 0 else 0.0
        cls_total = cm[i, :].sum()
        cls_acc   = TP / cls_total if cls_total > 0 else 0.0

        sens_list.append(sens)
        spec_list.append(spec)
        class_acc_list.append(cls_acc)

    # ── Macro Accuracy = 클래스별 accuracy 평균
    macro_acc = np.mean(class_acc_list)

    # ── ROC-AUC (multi-class OvR, macro)
    try:
        classes_present = np.unique(y_true)
        if len(classes_present) < 2:
            roc_auc = np.nan
        elif y_prob is not None and y_prob.shape[1] == n_cls:
            roc_auc = roc_auc_score(
                y_true, y_prob,
                multi_class="ovr", average="macro",
                labels=[0, 1, 2]
            )
        else:
            roc_auc = np.nan
    except Exception:
        roc_auc = np.nan

    return {
        "micro_acc": micro_acc,
        "macro_acc": macro_acc,
        "sens_0":    sens_list[0],   # 정상
        "sens_1":    sens_list[1],   # 경증
        "sens_2":    sens_list[2],   # 중증
        "avg_sens":  np.mean(sens_list),
        "avg_spec":  np.mean(spec_list),
        "roc_auc":   roc_auc,
    }


def aggregate_fold_metrics(fold_metrics):
    """fold별 지표 딕셔너리 리스트 → 평균 ± 표준편차."""
    keys = fold_metrics[0].keys()
    agg = {}
    for k in keys:
        vals = [m[k] for m in fold_metrics if not np.isnan(m[k])]
        agg[f"{k}_mean"] = np.mean(vals) if vals else np.nan
        agg[f"{k}_std"]  = np.std(vals)  if vals else np.nan
    return agg


# ──────────────────────────────────────────────────────────────
# 분류기 정의
# ──────────────────────────────────────────────────────────────

def get_classifiers():
    clfs = {
        "SVM": SVC(
            kernel="rbf", C=1.0, gamma="scale",
            class_weight="balanced",
            probability=True,
            random_state=CV_RANDOM_STATE
        ),
        "RF": RandomForestClassifier(
            n_estimators=RF_N_ESTIMATORS,
            class_weight="balanced",
            random_state=CV_RANDOM_STATE,
            n_jobs=-1
        ),
    }
    if HAS_XGB:
        clfs["XGBoost"] = XGBClassifier(
            n_estimators=XGB_N_ESTIMATORS,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=CV_RANDOM_STATE,
            n_jobs=-1,
            verbosity=0
        )
    return clfs


# ──────────────────────────────────────────────────────────────
# 메인 CV 루프
# ──────────────────────────────────────────────────────────────

def run_cv_pipeline(df_feat, feat_cols, verbose=True):
    """
    전체 파이프라인:
    ANOVA → 4종 FS → (각 FS × 각 분류기) BSS + StratifiedGroupKFold

    Returns
    -------
    results_df : pd.DataFrame  — 최종 성능 비교표
    """
    X_all        = df_feat[feat_cols].values.astype(float)
    y_all        = df_feat["장애정도"].values.astype(int)
    speaker_ids  = df_feat["speaker_id"].values
    feat_names   = np.array(feat_cols)

    # ── 전체 데이터로 ANOVA (참고용, 피처 필터링용 초기 분석)
    #    ※ 실제 모델 학습은 fold 내에서 train만 사용
    imputer_global = SimpleImputer(strategy="median")
    X_imp = imputer_global.fit_transform(X_all)

    sig_idx, sig_names, stat_df = run_anova_filter(
        X_imp, y_all, feat_names.tolist(), verbose=verbose
    )

    if len(sig_idx) == 0:
        print("[ERROR] 유의한 피처가 없습니다. 임계값 확인 요망.")
        return pd.DataFrame()

    # ── CV 설정 (중증 샘플 수 기반 fold 수 자동 조정)
    min_class_count = np.min(np.bincount(y_all))
    n_splits_actual = min(N_SPLITS, min_class_count)  # 클래스당 최소 샘플 수 이하로 fold 제한
    if n_splits_actual < N_SPLITS:
        print(f"  [조정] 중증 샘플({min_class_count}개) → {n_splits_actual}-fold CV 적용")

    # StratifiedGroupKFold: 화자 단위 분리 + 클래스 비율 유지
    sgkf = StratifiedGroupKFold(
        n_splits=n_splits_actual, shuffle=True, random_state=CV_RANDOM_STATE
    )
    classifiers = get_classifiers()

    # ── 결과 저장소
    all_results = []

    # ── 4종 FS × 3종 분류기
    fs_names = ["QoV", "RelieFF", "LASSO", "RelieFF2"]

    for fs_name in fs_names:
        if verbose:
            print(f"\n{'='*55}")
            print(f"[FS: {fs_name}]")

        for clf_name, clf_template in classifiers.items():
            if verbose:
                print(f"\n  [분류기: {clf_name}]")

            fold_metrics = []
            fold_n_features = []

            try:
                splits = list(sgkf.split(X_imp, y_all, groups=speaker_ids))
            except Exception as e:
                print(f"  [WARN] StratifiedGroupKFold 실패 ({e}), StratifiedKFold 대체")
                skf = StratifiedKFold(n_splits=n_splits_actual, shuffle=True,
                                      random_state=CV_RANDOM_STATE)
                splits = list(skf.split(X_imp, y_all))

            for fold_i, (train_idx, test_idx) in enumerate(splits):
                # ── 데이터 분할
                X_tr_raw, X_te_raw = X_all[train_idx], X_all[test_idx]
                y_tr, y_te         = y_all[train_idx], y_all[test_idx]
                spk_tr             = speaker_ids[train_idx]

                # ── Imputation (train만으로 fit)
                imp = SimpleImputer(strategy="median")
                X_tr = imp.fit_transform(X_tr_raw)
                X_te = imp.transform(X_te_raw)

                # ── 정규화 (train만으로 fit)
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X_tr)
                X_te = scaler.transform(X_te)

                # ── ANOVA 필터 (train 기준)
                from sklearn.feature_selection import f_classif as fc
                F_tr, p_tr = fc(X_tr, y_tr)
                sig_fold = np.where(p_tr < P_THRESHOLD)[0]
                if len(sig_fold) == 0:
                    sig_fold = np.argsort(F_tr)[-10:]  # 최소 10개 보장

                X_tr_sig = X_tr[:, sig_fold]
                X_te_sig = X_te[:, sig_fold]
                sig_names_fold = feat_names[sig_fold]

                # ── FS (train 기준으로 재计算)
                if fs_name == "QoV":
                    ranking = fs_qov_local(X_tr_sig, y_tr)
                elif fs_name == "RelieFF":
                    ranking = fs_relieff_local(X_tr_sig, y_tr, k=RELIEF_K)
                elif fs_name == "LASSO":
                    ranking = fs_lasso_local(X_tr_sig, y_tr)
                elif fs_name == "RelieFF2":
                    ranking = fs_relieff_local(X_tr_sig, y_tr, k=RELIEF2_K)
                else:
                    ranking = list(range(X_tr_sig.shape[1]))

                # ── 최적 N 탐색 (train 내부 3-fold로 간단 탐색)
                best_n, top_n_idx = get_initial_topN(
                    ranking, X_tr_sig, y_tr,
                    clone(clf_template), N_max=min(30, len(ranking))
                )

                # ── BSS (train ↔ val split으로 수행)
                val_size = max(1, int(len(y_tr) * 0.2))
                X_bss_tr = X_tr_sig[:-val_size]
                X_bss_val = X_tr_sig[-val_size:]
                y_bss_tr  = y_tr[:-val_size]
                y_bss_val = y_tr[-val_size:]

                best_subset, _ = backward_stepwise_selection(
                    X_bss_tr, y_bss_tr,
                    X_bss_val, y_bss_val,
                    top_n_idx, clone(clf_template),
                    verbose=False
                )

                # ── 최종 분류기 학습
                clf = clone(clf_template)
                clf.fit(X_tr_sig[:, best_subset], y_tr)
                y_pred = clf.predict(X_te_sig[:, best_subset])

                try:
                    y_prob = clf.predict_proba(X_te_sig[:, best_subset])
                except Exception:
                    y_prob = None

                # ── 지표 계산
                metrics = compute_metrics(y_te, y_pred, y_prob)
                fold_metrics.append(metrics)
                fold_n_features.append(len(best_subset))

                if verbose:
                    print(f"    Fold {fold_i+1}: "
                          f"MicroAcc={metrics['micro_acc']:.3f} "
                          f"MicroAcc={metrics['macro_acc']:.3f} "
                          f"Sens=(정상:{metrics['sens_0']:.3f},"
                          f"경증:{metrics['sens_1']:.3f},"
                          f"중증:{metrics['sens_2']:.3f}) "
                          f"AUC={metrics['roc_auc']:.3f} "
                          f"N_feat={len(best_subset)}")

            # ── fold 집계
            agg = aggregate_fold_metrics(fold_metrics)
            n_feat_mean = np.mean(fold_n_features)

            row = {
                "FS":           fs_name,
                "Classifier":   clf_name,
                "N_features":   f"{n_feat_mean:.1f}",
                "Micro_Acc":    f"{agg['micro_acc_mean']*100:.1f}±{agg['micro_acc_std']*100:.1f}",
                "Macro_Acc":    f"{agg['macro_acc_mean']*100:.1f}±{agg['macro_acc_std']*100:.1f}",
                "Sens_정상":    f"{agg['sens_0_mean']*100:.1f}±{agg['sens_0_std']*100:.1f}",
                "Sens_경증":    f"{agg['sens_1_mean']*100:.1f}±{agg['sens_1_std']*100:.1f}",
                "Sens_중증":    f"{agg['sens_2_mean']*100:.1f}±{agg['sens_2_std']*100:.1f}",
                "Avg_Sens":     f"{agg['avg_sens_mean']*100:.1f}±{agg['avg_sens_std']*100:.1f}",
                "Avg_Spec":     f"{agg['avg_spec_mean']*100:.1f}±{agg['avg_spec_std']*100:.1f}",
                "ROC_AUC":      f"{agg['roc_auc_mean']:.3f}±{agg['roc_auc_std']:.3f}",
                # 숫자 버전 (정렬용)
                "_micro_acc_num": agg["micro_acc_mean"],
                "_roc_auc_num":   agg["roc_auc_mean"],
            }
            all_results.append(row)

            if verbose:
                print(f"\n  ▶ {fs_name}+{clf_name} 평균 결과:")
                print(f"     Micro Acc : {row['Micro_Acc']}%")
                print(f"     Macro Acc : {row['Macro_Acc']}%")
                print(f"     Sens 정상 : {row['Sens_정상']}%")
                print(f"     Sens 경증 : {row['Sens_경증']}%")
                print(f"     Sens 중증 : {row['Sens_중증']}%")
                print(f"     Avg Sens  : {row['Avg_Sens']}%")
                print(f"     Avg Spec  : {row['Avg_Spec']}%")
                print(f"     ROC-AUC   : {row['ROC_AUC']}")
                print(f"     N 피처    : {row['N_features']}")

    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values("_micro_acc_num", ascending=False)

    # 내부 정렬용 컬럼 제거
    results_df = results_df.drop(
        columns=["_micro_acc_num", "_roc_auc_num"], errors="ignore"
    )

    return results_df


# ── fold 내 FS 함수 (import 순환 방지용 로컬 정의)

def fs_qov_local(X, y):
    from sklearn.feature_selection import f_classif
    F, _ = f_classif(X, y)
    return np.argsort(F)[::-1].tolist()


def fs_relieff_local(X, y, k=10):
    try:
        from ReliefF import ReliefF
        r = ReliefF(n_neighbors=k, n_features_to_keep=X.shape[1])
        r.fit(X, y)
        return r.top_features.tolist()
    except Exception:
        return fs_qov_local(X, y)


def fs_lasso_local(X, y):
    C_vals = np.logspace(LASSO_C_RANGE[0], LASSO_C_RANGE[1], LASSO_N_STEPS)
    order, activated = [], set()
    for C in C_vals:
        try:
            m = LogisticRegression(
                penalty="l1", solver="saga",
                multi_class="multinomial",
                C=C, max_iter=3000,
                random_state=CV_RANDOM_STATE
            )
            m.fit(X, y)
            active = set(np.where(np.any(m.coef_ != 0, axis=0))[0])
            newly = sorted(active - activated)
            order.extend(newly)
            activated = active
        except Exception:
            continue
    remaining = [i for i in range(X.shape[1]) if i not in order]
    order.extend(remaining)
    return order


if __name__ == "__main__":
    print("이 모듈은 run_all.py에서 호출됩니다.")

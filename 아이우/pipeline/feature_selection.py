"""
STEP 5-7: 통계 분석 + 4종 피처 선택 + BSS
출력: results/stat_analysis.csv, results/fs_rankings.json
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.base import clone

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *


# ──────────────────────────────────────────────────────────────
# STEP 5: ANOVA F-test (피어슨 r 대체)
# ──────────────────────────────────────────────────────────────

def run_anova_filter(X, y, feature_names, verbose=True):
    """
    각 피처와 레이블 간 ANOVA F-test 수행.
    p < P_THRESHOLD 통과 피처 인덱스 반환.
    """
    F_scores, p_values = f_classif(X, y)

    stat_df = pd.DataFrame({
        "Feature":  feature_names,
        "F_score":  F_scores,
        "p_value":  p_values,
        "significant": p_values < P_THRESHOLD,
    }).sort_values("F_score", ascending=False).reset_index(drop=True)

    stat_df.to_csv(STAT_CSV, index=False, encoding="utf-8-sig")

    sig_mask  = p_values < P_THRESHOLD
    sig_idx   = np.where(sig_mask)[0]
    sig_names = np.array(feature_names)[sig_idx]

    if verbose:
        print(f"\n[STEP 5] ANOVA F-test 결과")
        print(f"  유의한 피처: {len(sig_idx)} / {len(feature_names)}개 (p<{P_THRESHOLD})")
        print(f"  상위 10개:")
        print(stat_df[["Feature","F_score","p_value"]].head(10).to_string(index=False))
        print(f"  저장: {STAT_CSV}")

    return sig_idx, sig_names, stat_df


# ──────────────────────────────────────────────────────────────
# STEP 6: 4종 피처 선택 알고리즘
# ──────────────────────────────────────────────────────────────

def fs_qov(X, y, sig_names, verbose=True):
    """
    FS-1: QoV → ANOVA F-score 내림차순 랭킹.
    유의 피처 구간에서 F-score로 순위 결정.
    """
    F_scores, _ = f_classif(X, y)
    ranking = np.argsort(F_scores)[::-1].tolist()
    if verbose:
        print(f"\n[FS-QoV] 상위 5 피처: {[sig_names[i] for i in ranking[:5]]}")
    return ranking


def fs_relieff(X, y, sig_names, k=RELIEF_K, verbose=True):
    """
    FS-2/4: RelieFF (k-nearest neighbor, multi-class 지원).
    ReliefF 라이브러리 사용.
    """
    try:
        from ReliefF import ReliefF
        relief = ReliefF(n_neighbors=k, n_features_to_keep=X.shape[1])
        relief.fit(X, y)
        ranking = relief.top_features.tolist()
        if verbose:
            print(f"\n[FS-RelieFF k={k}] 상위 5 피처: {[sig_names[i] for i in ranking[:5]]}")
        return ranking
    except ImportError:
        print("  [WARN] ReliefF 미설치. pip install ReliefF")
        return list(range(X.shape[1]))


def fs_multinomial_lasso(X, y, sig_names, verbose=True):
    """
    FS-3: Multinomial LASSO.
    C를 작→크로 증가시키며 피처가 0에서 활성화되는 순서 = 중요도 순.
    """
    C_values = np.logspace(LASSO_C_RANGE[0], LASSO_C_RANGE[1], LASSO_N_STEPS)
    lasso_order = []
    activated   = set()

    for C in C_values:
        try:
            m = LogisticRegression(
                penalty="l1", solver="saga",
                multi_class="multinomial",
                C=C, max_iter=5000,
                random_state=CV_RANDOM_STATE
            )
            m.fit(X, y)
            active_now = set(np.where(np.any(m.coef_ != 0, axis=0))[0])
            newly = active_now - activated
            lasso_order.extend(sorted(newly))
            activated = active_now
        except Exception:
            continue

    # 아직 순서 미결정된 피처 → 맨 뒤에 추가
    all_idx = set(range(X.shape[1]))
    remaining = [i for i in range(X.shape[1]) if i not in lasso_order]
    lasso_order.extend(remaining)

    if verbose:
        print(f"\n[FS-LASSO] 활성화 피처 수: {len(activated)}")
        print(f"  상위 5 피처: {[sig_names[i] for i in lasso_order[:5]]}")

    return lasso_order


def run_feature_selection(X_sig, y, sig_names, verbose=True):
    """
    4종 FS 실행 → 각각 피처 랭킹 반환.

    Returns
    -------
    rankings : dict  {fs_name: [ordered_feature_indices]}
    """
    if verbose:
        print(f"\n[STEP 6] 4종 피처 선택 (유의 피처 {len(sig_names)}개 대상)")

    rankings = {}
    rankings["QoV"]      = fs_qov(X_sig, y, sig_names, verbose)
    rankings["RelieFF"]  = fs_relieff(X_sig, y, sig_names, k=RELIEF_K, verbose=verbose)
    rankings["LASSO"]    = fs_multinomial_lasso(X_sig, y, sig_names, verbose)
    rankings["RelieFF2"] = fs_relieff(X_sig, y, sig_names, k=RELIEF2_K, verbose=verbose)

    return rankings


# ──────────────────────────────────────────────────────────────
# STEP 7: BSS (Backward Stepwise Selection)
# ──────────────────────────────────────────────────────────────

def backward_stepwise_selection(X_train, y_train, X_val, y_val,
                                 initial_features, classifier,
                                 max_removals=None, verbose=False):
    """
    역방향 단계 선택: 성능에 부정적인 피처 순차 제거.

    Parameters
    ----------
    initial_features : list of int  — FS 알고리즘이 선택한 피처 인덱스 (이미 상위 N개)
    classifier       : sklearn 분류기 (clone 사용)

    Returns
    -------
    best_subset : list of int  — 최적 피처 서브셋 인덱스
    best_acc    : float        — 해당 서브셋 accuracy
    """
    current = list(initial_features)
    best_subset = list(current)

    clf = clone(classifier)
    clf.fit(X_train[:, current], y_train)
    best_acc = clf.score(X_val[:, current], y_val)

    if max_removals is None:
        max_removals = len(current) - 1

    for step in range(max_removals):
        if len(current) <= 1:
            break

        scores = []
        for i in range(len(current)):
            candidate = [current[j] for j in range(len(current)) if j != i]
            try:
                clf_tmp = clone(classifier)
                clf_tmp.fit(X_train[:, candidate], y_train)
                acc = clf_tmp.score(X_val[:, candidate], y_val)
                scores.append(acc)
            except Exception:
                scores.append(-np.inf)

        worst_i = int(np.argmin(scores))
        worst_acc_without = scores[worst_i]

        # 제거 후 성능이 현재 이상이면 제거
        new_features = [current[j] for j in range(len(current)) if j != worst_i]
        clf_new = clone(classifier)
        clf_new.fit(X_train[:, new_features], y_train)
        new_acc = clf_new.score(X_val[:, new_features], y_val)

        if new_acc >= best_acc:
            current = new_features
            best_acc = new_acc
            best_subset = list(current)
            if verbose:
                print(f"    BSS step {step+1}: 제거됨, 남은 피처 {len(current)}개, acc={new_acc:.4f}")
        else:
            if verbose:
                print(f"    BSS 종료: 더 이상 제거 불가 (step {step+1})")
            break

    return best_subset, best_acc


def get_initial_topN(ranking, X, y, classifier, N_max=50):
    """
    BSS 시작점 = ranking 상위 N개.
    N은 CV accuracy가 최대가 되는 값 (N=1~N_max에 대해 간단 탐색).
    """
    from sklearn.model_selection import cross_val_score, StratifiedKFold

    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=CV_RANDOM_STATE)
    best_n, best_score = 1, -np.inf

    for n in range(1, min(N_max, len(ranking)) + 1):
        sel = ranking[:n]
        try:
            scores = cross_val_score(clone(classifier), X[:, sel], y,
                                     cv=skf, scoring="accuracy")
            if np.mean(scores) > best_score:
                best_score = np.mean(scores)
                best_n = n
        except Exception:
            continue

    return best_n, ranking[:best_n]


if __name__ == "__main__":
    print("이 모듈은 run_all.py에서 호출됩니다.")

"""
[ Phase 9 - SHAP 시각화 ] 15차원 Cascade + SVM 메타 학습기 피처 기여도 분석
SHAP 0.51 API 호환 버전
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

warnings.filterwarnings("ignore")

# ── 한국어 폰트 설정 ─────────────────────────────────────────
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *

import shap
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix

# ── 경로 ──────────────────────────────────────────────────────
OOF_PROBS_NPY           = os.path.join(RESULTS_DIR, "oof_probs_15d_cascade.npy")
OOF_MASK_NPY            = os.path.join(RESULTS_DIR, "oof_mask_15d_cascade.npy")
HYBRID_AUG_FEATURES_CSV = os.path.join(RESULTS_DIR, "features_hybrid_augmented.csv")
OUTPUT_DIR              = os.path.join(RESULTS_DIR, "shap_plots")
BEST_THRESHOLD          = 0.160

# ── 15D 채널 이름 & 색상 ───────────────────────────────────────
FEAT_NAMES = [
    "LASSO-SVM │ P(정상)",
    "LASSO-SVM │ P(경증)",
    "LASSO-SVM │ P(중증)",
    "RelieFF-SVM │ P(정상)",
    "RelieFF-SVM │ P(경증)",
    "RelieFF-SVM │ P(중증)",
    "QoV-SVM │ P(정상)",
    "QoV-SVM │ P(경증)",
    "QoV-SVM │ P(중증)",
    "이진전문가 │ P(정상)",
    "이진전문가 │ P(경증)",
    "Cascade① │ P(정상)",
    "Cascade① │ P(비정상)",
    "Cascade② │ P(경증)",
    "Cascade② │ P(중증)",
]

GROUP_COLORS = (
    ["#A8D8EA"] * 3 +   # LASSO-SVM
    ["#A8D0A8"] * 3 +   # RelieFF-SVM
    ["#F4C2C2"] * 3 +   # QoV-SVM
    ["#FFE4B5"] * 2 +   # 이진 전문가
    ["#D8B4FE"] * 2 +   # Cascade①
    ["#FCA5A5"] * 2     # Cascade②
)

CLASS_NAMES  = ["정상(Normal)", "경증(Mild)", "중증(Severe)"]
CLASS_COLORS = ["#4A90D9", "#F5A623", "#E74C3C"]


def load_and_refit():
    oof_probs = np.load(OOF_PROBS_NPY)
    oof_mask  = np.load(OOF_MASK_NPY)

    df    = pd.read_csv(HYBRID_AUG_FEATURES_CSV, encoding="utf-8-sig")
    df    = df.dropna(subset=["장애정도"])
    y_all = df["장애정도"].values.astype(int)

    X_meta = oof_probs[oof_mask]
    y_meta = y_all[oof_mask]

    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X_meta)

    clf = SVC(kernel="rbf", C=10.0, gamma="scale",
              class_weight={0: 1.0, 1: 1.0, 2: 5.0},
              probability=True, random_state=42)
    clf.fit(X_sc, y_meta)
    return X_sc, y_meta, clf


def fix_shap_shape(raw, N, n_feat=15, n_cls=3):
    """
    SHAP 0.51이 반환하는 다양한 형태를 list[ndarray(N, n_feat)] (길이 n_cls)로 정규화.
    확인된 형태: List of N items, each shape (n_feat, n_cls).
    """
    if isinstance(raw, list) and len(raw) == N:
        first = np.array(raw[0])
        if first.ndim == 2 and first.shape == (n_feat, n_cls):
            # (N,) list of (n_feat, n_cls) → stack → (N, n_feat, n_cls)
            arr = np.stack([np.array(r) for r in raw], axis=0)  # (N, n_feat, n_cls)
            return [arr[:, :, c] for c in range(n_cls)]          # list of 3 × (N, n_feat)

    if isinstance(raw, list) and len(raw) == n_cls:
        # already list of n_cls × (N, n_feat)
        return raw

    # numpy array of shape (N, n_feat, n_cls)
    if isinstance(raw, np.ndarray) and raw.ndim == 3:
        return [raw[:, :, c] for c in range(n_cls)]

    raise ValueError(
        f"처리 불가능한 SHAP 형태: len={len(raw)}, "
        f"inner type={type(raw[0])}, inner shape={np.array(raw[0]).shape}"
    )


def compute_shap(X_sc, clf):
    print("  KMeans 배경 10개 생성 중...")
    bg = shap.kmeans(X_sc, 10)

    explainer   = shap.KernelExplainer(clf.predict_proba, bg)
    print("  KernelExplainer SHAP 계산 중 (nsamples=300)...")
    raw = explainer.shap_values(X_sc, nsamples=300)

    N, n_feat = X_sc.shape
    sv = fix_shap_shape(raw, N, n_feat, n_cls=3)
    print(f"  SHAP 정규화 완료 → 클래스별 형상: {[s.shape for s in sv]}")
    return sv   # list of 3 arrays, each (N=107, 15)


# ── 그래프 1: 클래스별 Mean |SHAP| 가로 막대 ──────────────────
def plot_bar_by_class(sv, output_dir):
    fig, axes = plt.subplots(1, 3, figsize=(21, 8))
    fig.suptitle("15D Cascade-SVM │ 클래스별 피처 기여도 (Mean |SHAP|)",
                 fontsize=16, fontweight="bold", y=1.01)

    for ci, (ax, cname, ccolor) in enumerate(zip(axes, CLASS_NAMES, CLASS_COLORS)):
        ma     = np.abs(sv[ci]).mean(axis=0)   # (15,)
        order  = np.argsort(ma)[::-1]

        ax.barh(range(15), ma[order],
                color=[GROUP_COLORS[i] for i in order],
                edgecolor="white", linewidth=0.7, height=0.75)
        ax.set_yticks(range(15))
        ax.set_yticklabels([FEAT_NAMES[i] for i in order], fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlabel("Mean |SHAP|", fontsize=10)
        ax.set_title(f"▶ {cname}", fontsize=12, fontweight="bold", color=ccolor)
        ax.spines[["top", "right"]].set_visible(False)
        for j, val in enumerate(ma[order]):
            ax.text(val + ma.max() * 0.01, j, f"{val:.4f}",
                    va="center", fontsize=7, color="#444")

    legend_patches = [
        mpatches.Patch(color="#A8D8EA", label="LASSO-SVM (3클래스)"),
        mpatches.Patch(color="#A8D0A8", label="RelieFF-SVM (3클래스)"),
        mpatches.Patch(color="#F4C2C2", label="QoV-SVM (3클래스)"),
        mpatches.Patch(color="#FFE4B5", label="이진전문가 (정상↔경증)"),
        mpatches.Patch(color="#D8B4FE", label="Cascade① (정상↔비정상)"),
        mpatches.Patch(color="#FCA5A5", label="Cascade② (경증↔중증)"),
    ]
    fig.legend(handles=legend_patches, loc="lower center",
               ncol=3, fontsize=9, framealpha=0.9,
               bbox_to_anchor=(0.5, -0.06))

    plt.tight_layout()
    path = os.path.join(output_dir, "shap_mean_abs_by_class.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {path}")
    return path


# ── 그래프 2: 전체 기여도 통합 막대 ──────────────────────────
def plot_bar_global(sv, output_dir):
    # 3클래스 절댓값 평균 → 피처별 중요도
    global_imp = np.mean([np.abs(s).mean(axis=0) for s in sv], axis=0)  # (15,)
    order = np.argsort(global_imp)[::-1]

    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(range(15), global_imp[order],
                   color=[GROUP_COLORS[i] for i in order],
                   edgecolor="white", linewidth=0.7, height=0.75)
    ax.set_yticks(range(15))
    ax.set_yticklabels([FEAT_NAMES[i] for i in order], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Mean |SHAP| (3클래스 통합)", fontsize=11)
    ax.set_title("전체 클래스 통합 피처 중요도 (15D Cascade-SVM 메타)",
                 fontsize=14, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

    for bar, val in zip(bars, global_imp[order]):
        ax.text(val + global_imp.max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.4f}", va="center", fontsize=8, color="#333")

    legend_patches = [
        mpatches.Patch(color="#A8D8EA", label="LASSO-SVM"), mpatches.Patch(color="#A8D0A8", label="RelieFF-SVM"),
        mpatches.Patch(color="#F4C2C2", label="QoV-SVM"),   mpatches.Patch(color="#FFE4B5", label="이진전문가"),
        mpatches.Patch(color="#D8B4FE", label="Cascade①"),  mpatches.Patch(color="#FCA5A5", label="Cascade②"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9, framealpha=0.85)

    plt.tight_layout()
    path = os.path.join(output_dir, "shap_global_importance.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {path}")
    return path


# ── 그래프 3: 클래스별 Beeswarm (scatter) ────────────────────
def plot_beeswarm(sv, X_sc, output_dir):
    paths = []
    for ci, (cname, ccolor) in enumerate(zip(CLASS_NAMES, CLASS_COLORS)):
        s      = sv[ci]                         # (N, 15)
        order  = np.argsort(np.abs(s).mean(axis=0))[::-1]

        fig, ax = plt.subplots(figsize=(12, 7))
        for fi in range(15):
            fi_orig = order[fi]
            y_jit   = fi + np.random.uniform(-0.25, 0.25, s.shape[0])
            sc = ax.scatter(s[:, fi_orig], y_jit,
                            c=X_sc[:, fi_orig], cmap="coolwarm",
                            alpha=0.7, s=35,
                            vmin=np.percentile(X_sc[:, fi_orig], 5),
                            vmax=np.percentile(X_sc[:, fi_orig], 95))

        ax.set_yticks(range(15))
        ax.set_yticklabels([FEAT_NAMES[i] for i in order], fontsize=8.5)
        ax.invert_yaxis()
        ax.axvline(0, color="black", lw=0.8, ls="--")
        ax.set_xlabel("SHAP 값  (← 예측 가능성 감소  │  증가 →)", fontsize=10)
        ax.set_title(f"SHAP Beeswarm │ {cname} 분류 기여도\n(빨강=피처값 높음, 파랑=낮음)",
                     fontsize=13, fontweight="bold", color=ccolor)
        ax.spines[["top", "right"]].set_visible(False)

        cbar = plt.colorbar(sc, ax=ax, pad=0.01)
        cbar.set_label("표준화된 피처값", fontsize=9)
        plt.tight_layout()

        suffix = ["normal", "mild", "severe"][ci]
        path = os.path.join(output_dir, f"shap_beeswarm_{suffix}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  ✅ {path}")
        paths.append(path)
    return paths


# ── 그래프 4: 대표 케이스 Waterfall style ────────────────────
def plot_waterfall(sv, X_sc, y_meta, clf, output_dir):
    meta_probs = clf.predict_proba(X_sc)
    preds = np.argmax(meta_probs, axis=1)
    preds[meta_probs[:, 2] >= BEST_THRESHOLD] = 2

    paths = []
    for ci, (cname, ccolor) in enumerate(zip(CLASS_NAMES, CLASS_COLORS)):
        idx = np.where(y_meta == ci)[0]
        if len(idx) == 0:
            continue
        best_i = idx[np.argmax(meta_probs[idx, ci])]

        s          = sv[ci][best_i]             # (15,)
        feat_order = np.argsort(np.abs(s))[::-1]

        fig, ax = plt.subplots(figsize=(11, 7))
        colors = ["#E74C3C" if v >= 0 else "#4A90D9" for v in s[feat_order]]
        ax.barh(range(15), s[feat_order], color=colors,
                edgecolor="white", height=0.7)
        ax.set_yticks(range(15))
        ax.set_yticklabels([FEAT_NAMES[i] for i in feat_order], fontsize=8.5)
        ax.invert_yaxis()
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlabel("SHAP value (빨강=예측 강화, 파랑=예측 억제)", fontsize=10)
        ax.set_title(
            f"SHAP Waterfall │ {cname} 대표 케이스\n"
            f"실제: {CLASS_NAMES[y_meta[best_i]]} | 예측: {CLASS_NAMES[preds[best_i]]} | "
            f"P({cname[:2]})={meta_probs[best_i, ci]:.3f}",
            fontsize=12, fontweight="bold", color=ccolor
        )
        ax.spines[["top", "right"]].set_visible(False)

        xmax = np.abs(s).max()
        for j, (val, fi) in enumerate(zip(s[feat_order], feat_order)):
            offset = xmax * 0.02
            ha = "left" if val >= 0 else "right"
            ax.text(val + (offset if val >= 0 else -offset), j,
                    f"{val:+.4f}", va="center", ha=ha, fontsize=7.5)

        plt.tight_layout()
        suffix = ["normal", "mild", "severe"][ci]
        path = os.path.join(output_dir, f"shap_waterfall_{suffix}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  ✅ {path}")
        paths.append(path)
    return paths


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  🔬 [ SHAP 분석 ] 15D Cascade-SVM 메타 학습기 피처 기여도   ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    print("▶ STEP 1: OOF 데이터 로드 및 메타 SVM 재훈련")
    X_sc, y_meta, clf = load_and_refit()
    print(f"  형상: {X_sc.shape} | 클래스: {dict(zip(*np.unique(y_meta, return_counts=True)))}")

    print("\n▶ STEP 2: SHAP 계산 (약 2~3분)")
    sv = compute_shap(X_sc, clf)

    print("\n▶ STEP 3: 시각화 생성")
    p1 = plot_bar_by_class(sv, OUTPUT_DIR)
    p2 = plot_bar_global(sv, OUTPUT_DIR)
    p3 = plot_beeswarm(sv, X_sc, OUTPUT_DIR)
    p4 = plot_waterfall(sv, X_sc, y_meta, clf, OUTPUT_DIR)

    all_paths = [p1, p2] + p3 + p4
    print(f"\n{'='*60}")
    print(f"🎉 총 {len(all_paths)}개 SHAP 시각화 완료!")
    print(f"📂 저장 폴더: {OUTPUT_DIR}")
    for p in all_paths:
        print(f"   - {os.path.basename(p)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

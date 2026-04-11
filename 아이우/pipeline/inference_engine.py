"""
말길(MalGil) AI 추론 엔진 — 15D Cascade-SVM 마스터 모델 (Wav2Vec2 제거 버전)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 입력: 아/이/우 모음 발성 wav 파일 3개
- 피처: Praat 임상 음향 피처 112차원 (W2V 완전 제거)
- 모델: 15D Cascade-SVM 메타 앙상블
  ch  1- 3 : 3클래스 QoV SVM
  ch  4- 6 : 3클래스 RelieFF SVM
  ch  7- 9 : 3클래스 LASSO SVM
  ch 10-11 : 정상↔경증 이진 SVM
  ch 12-13 : 정상 vs 비정상 Cascade SVM
  ch 14-15 : 경증 vs 중증 Cascade SVM
  → SVM(RBF) 메타 학습기 + Youden-J 임계값
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import os, sys, warnings, joblib
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.config import *
from pipeline.feature_extractor import extract_session_features

MODELS_DIR         = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
CASCADE_MASTER_PKL = os.path.join(MODELS_DIR, "master_model_cascade_15d.pkl")
FEAT_REF_CSV       = os.path.join(RESULTS_DIR, "features_hybrid_augmented_v2.csv")


class DysarthriaInferenceEngine:
    """
    15D Cascade-SVM 기반 조음장애 중증도 분류 추론 엔진.
    Wav2Vec2 완전 제거 — 임상 해석 가능한 Praat 피처(112차원)만 사용.
    """

    def __init__(self):
        print("=== 말길(MalGil) AI 추론 엔진 초기화 시작 (15D Cascade W2V-Free) ===")

        # 1. Cascade 마스터 모델 로딩
        if not os.path.exists(CASCADE_MASTER_PKL):
            raise FileNotFoundError(
                f"Cascade 마스터 모델이 없습니다: {CASCADE_MASTER_PKL}\n"
                "pipeline/train_cascade_master_model.py 를 먼저 실행하세요."
            )
        self.cascade = joblib.load(CASCADE_MASTER_PKL)
        perf = self.cascade.get("performance", {})
        print(f"  [Cascade 15D] 로딩 완료")
        print(f"    Base SVM 6종 | 메타 SVM | 임계값: {self.cascade['best_threshold']:.3f}")
        print(f"    학습 성능 — Micro Acc: {perf.get('micro_acc','?')}% | "
              f"정상: {perf.get('sens_정상','?')}% | "
              f"경증: {perf.get('sens_경증','?')}% | "
              f"중증: {perf.get('sens_중증','?')}%")

        # 2. 피처 컬럼 순서 확정 (학습 시와 동일해야 함)
        meta_cols = {"UID", "speaker_id", "장애정도", "augmented", "aug_type"}
        if "feature_names" in self.cascade and self.cascade["feature_names"]:
            self.feat_cols = self.cascade["feature_names"]
        elif os.path.exists(FEAT_REF_CSV):
            df_ref = pd.read_csv(FEAT_REF_CSV, nrows=1, encoding="utf-8-sig")
            self.feat_cols = [
                c for c in df_ref.columns
                if c not in meta_cols and not c.startswith("W2V_")
            ]
        else:
            self.feat_cols = None   # 첫 호출 시 자동 초기화

        if self.feat_cols:
            print(f"  피처 컬럼 {len(self.feat_cols)}개 확정")

        print("=== 초기화 완료 ===\n")

    # ──────────────────────────────────────────────────────────────────────────
    def extract_features(self, path_a, path_i, path_u):
        """3모음 wav → Praat 임상 피처 112차원 ndarray 반환."""
        row = {
            "UID": "user_inference", "speaker_id": "user", "장애정도": 0,
            "path_아": path_a, "path_이": path_i, "path_우": path_u,
        }
        praat_feats = extract_session_features(row, verbose=False)

        # feat_cols 첫 호출 시 자동 초기화
        if self.feat_cols is None:
            meta_cols = {"UID", "speaker_id", "장애정도", "augmented", "aug_type"}
            self.feat_cols = [
                k for k in praat_feats.keys()
                if k not in meta_cols and not k.startswith("W2V_")
            ]

        final_row    = {col: praat_feats.get(col, np.nan) for col in self.feat_cols}
        df_inference = pd.DataFrame([final_row])
        return df_inference.values.astype(float)   # (1, 112)

    # ──────────────────────────────────────────────────────────────────────────
    def _build_15d_vector(self, X_raw):
        """
        Praat 피처 112차원 → 15D 메타 피처 벡터 생성.
        Base SVM 6종을 순서대로 적용.
        """
        imp     = self.cascade["imputer"]
        scaler  = self.cascade["scaler"]
        sig_idx = self.cascade["sig_idx"]

        X_imp   = imp.transform(X_raw)
        X_sc    = scaler.transform(X_imp)
        X_sig   = X_sc[:, sig_idx]         # (1, n_sig)

        fold_probs = []
        for bm in self.cascade["base_models"]:
            X_final = X_sig[:, bm["best_subset"]]
            probs   = bm["clf"].predict_proba(X_final)   # (1, n_classes)
            fold_probs.append(probs)

        stacked = np.hstack(fold_probs)    # (1, 15)
        return stacked

    # ──────────────────────────────────────────────────────────────────────────
    def predict(self, path_a, path_i, path_u):
        """
        3모음 wav 경로 입력 → 15D Cascade-SVM 진단 결과 반환.

        Returns
        -------
        dict
            recommended_result : int  — Youden-J 임계값 적용 최종 판독 (✅ 주력)
            soft_avg_result    : int  — 평균 확률 기반 판독 (참고)
            class_probabilities: list — 정상/경증/중증 확률
            threshold_used     : float
        """
        X_raw   = self.extract_features(path_a, path_i, path_u)

        # 15D 메타 피처 생성
        X_15d   = self._build_15d_vector(X_raw)

        # 메타 학습기 추론
        meta_scaler = self.cascade["meta_scaler"]
        meta_clf    = self.cascade["meta_classifier"]
        best_th     = self.cascade["best_threshold"]

        X_15d_sc    = meta_scaler.transform(X_15d)
        meta_probs  = meta_clf.predict_proba(X_15d_sc)[0]       # (3,)

        # ── Youden-J 임계값 적용 (주력 판독) ───────────────────────────────
        recommended = int(np.argmax(meta_probs))
        if meta_probs[2] >= best_th:
            recommended = 2

        # ── 소프트 평균 (참고용) ─────────────────────────────────────────────
        soft_avg = int(np.argmax(meta_probs))

        label_map = {0: "정상", 1: "경증", 2: "중증"}

        return {
            "status":  "success",
            "message": "15D Cascade-SVM 진단 완료 (W2V-Free)",
            "recommended_result":  recommended,
            "recommended_label":   label_map[recommended],
            "soft_avg_result":     soft_avg,
            "class_probabilities": {
                "정상": round(float(meta_probs[0]) * 100, 1),
                "경증": round(float(meta_probs[1]) * 100, 1),
                "중증": round(float(meta_probs[2]) * 100, 1),
            },
            "threshold_used": best_th,
        }


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = DysarthriaInferenceEngine()
    print("Cascade Inference Engine (W2V-Free) is ready!")
    # 실제 경로로 테스트할 때:
    # result = engine.predict("path_아.wav", "path_이.wav", "path_우.wav")
    # print(result)

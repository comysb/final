"""
이음 4개 영역 점수 계산 엔진 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
공식: Domain_Score = Σ(feature_normalized × model_weight) × 100

기준값 출처:
  퍼터커: features_emb_all.csv 훈련 데이터 (정상 38명 p5/p95, 중증 5명 p5/p95)
  아이우: 임상 문헌값 (ADA 기준 + 한국어 정상 성인 기준)
  단어  : healthy_stats.joblib 정상인 통계 (mean ± 2std)

모델 F1 가중치:
  아이우:      0.944  (Micro Acc @ Youden-J 0.35 임계값)
  퍼터커:      0.850  (ResNet+Fusion+MLP, 5-fold 추정)
  단어:        0.780  (XGBoost+Wav2Vec2, 추정)

영역 매핑:
  발성(Phonation):   Jitter, Shimmer, NHR (아이우) + Jitter, Shimmer, APQ (단어)
  호흡(Respiration): MPT (아이우) + Energy, Pause시간 (퍼터커) + Energy (단어)
  조음(Articulation):VSA/FCR/VAI (아이우) + DDK, 명료도 (퍼터커) + CRR/VRR/PRR (단어)
  운율(Prosody):     F0_SD (아이우) + F0변동, Pause빈도 (퍼터커)
"""
import numpy as np

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 모델 F1 가중치
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODEL_F1 = {
    "aiiu":      0.944,
    "putterker": 0.850,
    "word":      0.780,
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 피처 기준값: (x_best, x_worst, direction)
#    direction: 'higher'=높을수록 좋음, 'lower'=낮을수록 좋음
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 퍼터커 기준값 (훈련 데이터 실측 percentile)
# 정상 p5/p95, 중증 p5/p95 기반
PUTTERKER_REFS = {
    # 조음
    "ddk_rate":              (4.80,  1.66,   "higher"),  # 정상p95=4.80, 중증p5=1.66
    "ddk_mean_dur_ms":       (86.41, 235.82, "lower"),   # 정상p5=86.41, 중증p95=235.82
    "ddk_regularity_ms":     (13.89, 290.06, "lower"),   # 정상p5=13.89, 중증p95=290.06
    "intelligibility_score": (82.15, 50.00,  "higher"),  # 정상p95=82.15, 중증p5=50.00
    # 호흡
    "mean_energy_db":        (68.25, 48.36,  "higher"),  # 정상p95, 중증p5
    "max_energy_db":         (86.16, 70.20,  "higher"),
    "var_energy_db":         (6.14,  11.51,  "lower"),   # 정상p5, 중증p95
    "pause_mean_dur_ms":     (157.69, 475.14, "lower"),  # 정상p5, 중증p95
    # 운율
    "f0_var_semitones":      (0.96,  8.00,   "lower"),   # 정상p5, 중증p95
    "f0_var_hz":             (10.78, 86.41,  "lower"),
    "pause_rate":            (0.23,  1.19,   "lower"),
    "pause_regularity_ms":   (4.25,  300.24, "lower"),
}

# 아이우 기준값 (임상 문헌 + 한국어 성인 기준)
AIIU_REFS = {
    # 호흡: MPT
    "MPT_아": (20.0, 4.0,  "higher"),
    "MPT_이": (20.0, 4.0,  "higher"),
    "MPT_우": (18.0, 4.0,  "higher"),
    # 발성: Jitter (ADA 기준 local < 1.04%)
    "jitter_local_아":    (0.005, 0.12, "lower"),
    "jitter_local_이":    (0.005, 0.12, "lower"),
    "jitter_local_우":    (0.005, 0.12, "lower"),
    "jitter_ddp_아":      (0.015, 0.35, "lower"),
    "jitter_ddp_이":      (0.015, 0.35, "lower"),
    "jitter_ddp_우":      (0.015, 0.35, "lower"),
    # 발성: Shimmer (ADA 기준 local < 3.81%)
    "shimmer_local_아":   (0.030, 0.30, "lower"),
    "shimmer_local_이":   (0.030, 0.30, "lower"),
    "shimmer_local_우":   (0.030, 0.30, "lower"),
    # 발성: NHR
    "nhr_아": (0.010, 0.45, "lower"),
    "nhr_이": (0.010, 0.45, "lower"),
    "nhr_우": (0.010, 0.45, "lower"),
    # 운율: F0 표준편차
    "F0_SD_아": (5.0, 35.0, "lower"),
    "F0_SD_이": (5.0, 35.0, "lower"),
    "F0_SD_우": (5.0, 35.0, "lower"),
    # 조음: 모음 공간 지수
    "VSA":      (280000.0, 20000.0,  "higher"),
    "FCR":      (0.75,     1.65,     "lower"),
    "VAI":      (0.95,     0.40,     "higher"),
    "F2이_F2우": (3.20,   1.30,     "higher"),
}

# 단어 기준값 (healthy_stats.joblib 기반: x_best = mean+2std)
WORD_REFS = {
    # 조음: 음소 인식률
    "crr":          (81.0,    0.0,    "higher"),  # 55.89 + 2×12.57
    "vrr":          (98.0,    0.0,    "higher"),  # 73.04 + 2×12.82 (cap)
    "prr":          (89.7,    0.0,    "higher"),  # 62.29 + 2×13.72
    # 조음: 모음 공간
    "vsa_triangle": (310000.0, 5000.0, "higher"),  # 118096 + 2×96043
    "fcr":          (0.88,    2.10,   "lower"),   # 1.34 - 2×0.23
    "vai":          (1.03,    0.30,   "higher"),  # 0.77 + 2×0.13
    "f2_ratio":     (2.86,    0.60,   "higher"),  # 1.73 + 2×0.56
    # 발성: 음질 지표
    "jitter":       (0.011,   0.15,   "lower"),   # 0.024 - 2×0.006
    "shimmer":      (0.083,   0.40,   "lower"),   # 0.132 - 2×0.024
    "apq":          (0.034,   0.30,   "lower"),   # 0.076 - 2×0.021
    # 호흡: 에너지 (dB 스케일)
    "mean_energy":  (70.6,    50.0,   "higher"),  # 63.88 + 2×3.35
    "std_energy":   (6.4,     22.0,   "lower"),   # 11.05 - 2×2.32 best; worst = mean+5std
}

ALL_REFS = {
    "aiiu":      AIIU_REFS,
    "putterker": PUTTERKER_REFS,
    "word":      WORD_REFS,
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 영역별 피처 매핑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN_FEATURES = {
    "발성": {
        "aiiu":      ["jitter_local_아", "jitter_local_이", "jitter_local_우",
                      "jitter_ddp_아",   "jitter_ddp_이",
                      "shimmer_local_아","shimmer_local_이","shimmer_local_우",
                      "nhr_아",          "nhr_이",          "nhr_우"],
        "putterker": [],
        "word":      ["jitter", "shimmer", "apq"],
    },
    "호흡": {
        "aiiu":      ["MPT_아", "MPT_이", "MPT_우"],
        "putterker": ["mean_energy_db", "var_energy_db", "max_energy_db",
                      "pause_mean_dur_ms"],
        "word":      ["mean_energy", "std_energy"],
    },
    "조음": {
        "aiiu":      ["VSA", "FCR", "VAI", "F2이_F2우"],
        "putterker": ["ddk_rate", "ddk_mean_dur_ms", "ddk_regularity_ms",
                      "intelligibility_score"],
        "word":      ["crr", "vrr", "prr", "vsa_triangle", "fcr", "vai", "f2_ratio"],
    },
    "운율": {
        "aiiu":      ["F0_SD_아", "F0_SD_이", "F0_SD_우"],
        "putterker": ["f0_var_hz", "f0_var_semitones", "pause_rate",
                      "pause_regularity_ms"],
        "word":      [],
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 핵심 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def normalize_feature(value, x_best, x_worst, direction):
    """단일 피처를 [0, 1]로 정규화. None/NaN 입력 시 None 반환."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None

    if direction == "higher":
        score = (v - x_worst) / (x_best - x_worst + 1e-9)
    else:  # lower
        score = (x_worst - v) / (x_worst - x_best + 1e-9)

    return float(np.clip(score, 0.0, 1.0))


def compute_domain_scores(putterker_features: dict,
                           aiiu_features: dict,
                           word_features: dict) -> dict:
    """
    3개 모델 raw 피처 딕셔너리 → 4개 영역 점수(0~100) 딕셔너리 반환.

    Parameters
    ----------
    putterker_features : 퍼터커 피처 12개 {'f0_var_hz': ..., ...}
    aiiu_features      : 아이우 Praat 피처 딕셔너리 (없으면 {} 전달)
    word_features      : 단어 raw 피처 딕셔너리    (없으면 {} 전달)

    Returns
    -------
    {'발성': 72.3, '호흡': 58.1, '조음': 45.6, '운율': 63.0}
    None 값은 해당 영역 데이터 부족
    """
    available = {
        "putterker": putterker_features or {},
        "aiiu":      aiiu_features      or {},
        "word":      word_features      or {},
    }
    domain_scores = {}

    for domain, model_feat_map in DOMAIN_FEATURES.items():
        weighted_sum  = 0.0
        total_weight  = 0.0
        detail_log    = {}   # 디버깅용

        for model_name, feat_list in model_feat_map.items():
            if not feat_list:
                continue
            refs      = ALL_REFS[model_name]
            model_f1  = MODEL_F1[model_name]
            feat_data = available[model_name]

            valid_scores = []
            for feat in feat_list:
                if feat not in feat_data or feat not in refs:
                    continue
                x_best, x_worst, direction = refs[feat]
                norm = normalize_feature(feat_data[feat], x_best, x_worst, direction)
                if norm is not None:
                    valid_scores.append(norm)
                    detail_log[feat] = round(norm, 3)

            if not valid_scores:
                continue

            model_avg = float(np.mean(valid_scores))
            # 가중치 = F1 × 사용된 피처 수 (많은 피처 = 신뢰도 높음)
            weight = model_f1 * len(valid_scores)
            weighted_sum += model_avg * weight
            total_weight  += weight

        if total_weight > 0:
            domain_scores[domain] = round((weighted_sum / total_weight) * 100, 1)
        else:
            domain_scores[domain] = None

    return domain_scores


def interpret_score(score) -> dict:
    """점수(0~100)를 등급·색상·메시지로 변환."""
    if score is None:
        return {"level": "미측정", "color": "#9CA3AF", "message": "측정 데이터 없음"}
    s = float(score)
    if s >= 75:
        return {"level": "양호",      "color": "#3B82F6", "message": "정상 범위에 가깝습니다"}
    elif s >= 55:
        return {"level": "경미",      "color": "#10B981", "message": "경미한 저하가 관찰됩니다"}
    elif s >= 35:
        return {"level": "훈련 필요", "color": "#F59E0B", "message": "집중 훈련이 필요합니다"}
    else:
        return {"level": "심각",      "color": "#EF4444", "message": "전문가 상담을 권장합니다"}


def build_full_report(putterker_features, aiiu_features, word_features) -> dict:
    """
    영역 점수 + 해석 + 종합 평가를 한 번에 반환하는 최상위 함수.

    Returns
    -------
    {
        'domain_scores': {'발성': 72.3, '호흡': 58.1, ...},
        'interpretations': {'발성': {'level': '양호', 'color': ..., 'message': ...}, ...},
        'overall_score': 59.7,
        'overall_level': '경미'
    }
    """
    scores = compute_domain_scores(putterker_features, aiiu_features, word_features)

    interpretations = {d: interpret_score(s) for d, s in scores.items()}

    valid_scores = [s for s in scores.values() if s is not None]
    overall = round(float(np.mean(valid_scores)), 1) if valid_scores else None

    return {
        "domain_scores":   scores,
        "interpretations": interpretations,
        "overall_score":   overall,
        "overall_level":   interpret_score(overall)["level"] if overall is not None else "미측정",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 단독 실행 시 last_predict_trace.json으로 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    import json, os

    trace_path = os.path.join(os.path.dirname(__file__), "last_predict_trace.json")
    if not os.path.exists(trace_path):
        print("[테스트] last_predict_trace.json 없음")
    else:
        with open(trace_path, encoding="utf-8") as f:
            trace = json.load(f)

        pk = trace.get("putterker", {}).get("features", {})
        ai = {}   # 아이우 raw 피처 (현재 API 미포함)
        wd = trace.get("word", {}).get("metrics", {})

        report = build_full_report(pk, ai, wd)

        print("=" * 50)
        print("  이음 영역별 점수 리포트")
        print("=" * 50)
        for domain, score in report["domain_scores"].items():
            info = report["interpretations"][domain]
            print(f"  {domain:6s}: {str(score):6s}점  [{info['level']:6s}]  {info['message']}")
        print(f"\n  종합 점수: {report['overall_score']}점  [{report['overall_level']}]")
        print("=" * 50)

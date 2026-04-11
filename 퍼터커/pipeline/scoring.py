"""
scoring.py
퍼터커 분류 모델의 예측 결과를 0~100점의 연속형 '발음 평가 점수'로 변환하는 모듈.
Method C: 임계값 기준 계층적 점수화 (Tiered Scoring via Thresholds) 방식을 사용합니다.
"""
import math

def calculate_putterker_score(prob_normal: float, prob_mild: float, prob_severe: float, 
                              thresh_binary: float, thresh_severe: float) -> dict:
    """
    3-Class Softmax 확률값과 Youden's J 임계값을 기반으로 100점 만점 발음 점수 산출
    
    Args:
        prob_normal: 정상(0) 클래스 예측 확률 (0.0 ~ 1.0)
        prob_mild: 경증(1) 클래스 예측 확률 (0.0 ~ 1.0)
        prob_severe: 중증(2) 클래스 예측 확률 (0.0 ~ 1.0)
        thresh_binary: 정상과 비정상(경증+중증)을 구분하는 최적 임계값 (예: 0.45)
        thresh_severe: 비정상 중 경증과 중증을 구분하는 최적 임계값 (예: 0.60)
        
    Returns:
        dict: {
            "score": int (0~100),
            "severity_label": str ("정상", "경증", "중증"),
            "severity_class": int (0, 1, 2)
        }
    """
    # 1. 비정상(Anomaly) 확률 및 중증(Severe) 비율 계산
    prob_anomaly = prob_mild + prob_severe
    
    # 분모가 0이 되는 것을 방지하기 위해 1e-8 추가
    severe_ratio = prob_severe / (prob_anomaly + 1e-8) if prob_anomaly > 0 else 0.0
    
    # 2. 임계값(Threshold)에 따른 클래스 판정 및 계층적 점수(Tier) 산출
    if prob_anomaly < thresh_binary:
        # ---------------------------------------------------------
        # [정상 구간]: 80점 ~ 100점
        # - prob_anomaly가 0에 가까울수록 100점 (퍼펙트 정상)
        # - prob_anomaly가 thresh_binary에 가까울수록 80점 (턱걸이 정상)
        # ---------------------------------------------------------
        severity_class = 0
        severity_label = "정상"
        
        # 선형 보간 (Linear Interpolation)
        ratio_in_tier = prob_anomaly / (thresh_binary + 1e-8)
        score_float = 100.0 - (ratio_in_tier * 20.0) 
        score = max(80, min(100, round(score_float)))
        
    else:
        if severe_ratio < thresh_severe:
            # ---------------------------------------------------------
            # [경증 구간]: 40점 ~ 79점
            # - severe_ratio가 0에 가까울수록(경증 확신) 79점
            # - severe_ratio가 thresh_severe에 가까울수록(중증 의심) 40점
            # ---------------------------------------------------------
            severity_class = 1
            severity_label = "경증"
            
            ratio_in_tier = severe_ratio / (thresh_severe + 1e-8)
            score_float = 79.0 - (ratio_in_tier * 39.0)
            score = max(40, min(79, round(score_float)))
            
        else:
            # ---------------------------------------------------------
            # [중증 구간]: 0점 ~ 39점
            # - severe_ratio가 thresh_severe에 가까울수록(경계선) 39점
            # - severe_ratio가 1.0에 가까울수록(완전 중증) 0점
            # ---------------------------------------------------------
            severity_class = 2
            severity_label = "중증"
            
            # severe_ratio의 구간은 [thresh_severe, 1.0]
            # 이를 [0.0, 1.0] 스케일로 변환
            ratio_in_tier = (severe_ratio - thresh_severe) / (1.0 - thresh_severe + 1e-8)
            score_float = 39.0 - (ratio_in_tier * 39.0)
            score = max(0, min(39, round(score_float)))
            
    return {
        "score": score,
        "severity_label": severity_label,
        "severity_class": severity_class,
        "details": {
            "probs": [float(round(prob_normal, 4)), float(round(prob_mild, 4)), float(round(prob_severe, 4))],
            "prob_anomaly": float(round(prob_anomaly, 4)),
            "severe_ratio": float(round(severe_ratio, 4))
        }
    }


# 테스트 코드 (단독 실행용)
if __name__ == "__main__":
    print("=== Putterker Tiered Scoring (Method C) Test ===")
    t_bin = 0.45
    t_sev = 0.60
    
    test_cases = [
        # 정상 (확실)
        [0.90, 0.08, 0.02],
        # 정상 (턱걸이)
        [0.56, 0.30, 0.14], # anomaly = 0.44 < 0.45
        # 경증 (확실)
        [0.20, 0.70, 0.10], # anomaly = 0.80 > 0.45, ratio = 0.1/0.8 = 0.125 < 0.60
        # 경증 (중증에 매우 가까움)
        [0.10, 0.40, 0.50], # anomaly = 0.90 > 0.45, ratio = 0.5/0.9 = 0.55 < 0.60
        # 중증 (완전 심각)
        [0.01, 0.04, 0.95], # anomaly = 0.99 > 0.45, ratio = 0.95/0.99 = 0.96 > 0.60
    ]
    
    print(f"설정된 임계값 (thresh_binary={t_bin}, thresh_severe={t_sev})\n")
    
    for i, probs in enumerate(test_cases):
        res = calculate_putterker_score(probs[0], probs[1], probs[2], t_bin, t_sev)
        print(f"Test {i+1} - 모델 확률: {res['details']['probs']}")
        print(f"  └> [진단]: {res['severity_label']} | [점수]: {res['score']}점")
        print(f"  └> (Anomaly Prob: {res['details']['prob_anomaly']} | Severe Ratio: {res['details']['severe_ratio']})\n")

"""
파이프라인 전역 설정
뇌졸중 후 조음장애 중증도 분류 (Vashkevich 2021 기반)
"""
import os

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR    = r"D:\아이우"
DIR_A       = os.path.join(BASE_DIR, "1")   # /아/ (task 001)
DIR_I       = os.path.join(BASE_DIR, "7")   # /이/ (task 007)
DIR_U       = os.path.join(BASE_DIR, "8")   # /우/ (task 008)
XLSX_PATH   = os.path.join(BASE_DIR, "data.xlsx")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── 결과 파일 경로 ─────────────────────────────────────────
MAPPING_CSV   = os.path.join(RESULTS_DIR, "session_mapping.csv")
FEATURES_CSV  = os.path.join(RESULTS_DIR, "features.csv")
STAT_CSV      = os.path.join(RESULTS_DIR, "stat_analysis.csv")
FS_JSON       = os.path.join(RESULTS_DIR, "fs_rankings.json")
RESULTS_CSV   = os.path.join(RESULTS_DIR, "final_results.csv")
REPORT_HTML   = os.path.join(RESULTS_DIR, "report.html")

# ── 오디오 설정 ────────────────────────────────────────────
TARGET_SR        = 44100       # 목표 샘플레이트 (Hz)
STABLE_RATIO     = 0.80        # 안정구간 비율 (앞뒤 10% 제거)
MIN_DURATION_SEC = 1.0         # 최소 발성 길이 (초)

# ── Praat 파라미터 ─────────────────────────────────────────
PITCH_FLOOR  = 75    # F0 하한 (Hz) - 병리음성 포함
PITCH_CEIL   = 600   # F0 상한 (Hz)
F0_TIME_STEP = 0.01  # F0 추출 시간 간격 (초)

JITTER_PERIOD_FLOOR    = 0.0001
JITTER_PERIOD_CEIL     = 0.02
JITTER_MAX_FACTOR      = 1.3

SHIMMER_MAX_AMPLITUDE  = 1.6   # amplitude factor

FORMANT_MAX_FORMANT    = 5500  # Hz (여성 기준 여유)
FORMANT_NUM            = 5
FORMANT_WIN_LEN        = 0.025
FORMANT_PRE_EMPHASIS   = 50

HNR_TIME_STEP          = 0.01
HNR_MIN_PITCH          = 75
HNR_SILENCE_THRESH     = 0.1
HNR_PERIODS_PER_WIN    = 1.0

# ── MFCC 파라미터 ──────────────────────────────────────────
N_MFCC      = 13
N_FFT       = 2048
HOP_LENGTH  = 512
FMAX        = 8000   # Hz

# ── 레이블 매핑 ────────────────────────────────────────────
CLASS_NAMES = {0: "정상", 1: "경증", 2: "중증"}
N_CLASSES   = 3

# ── 피처 선택 설정 ─────────────────────────────────────────
P_THRESHOLD     = 0.05      # 유의수준
RELIEF_K        = 10        # RelieFF k-nearest
RELIEF2_K       = 20        # RelieFF 변형 k
LASSO_C_RANGE   = (-3, 2)   # logspace 범위 (C = 1/λ)
LASSO_N_STEPS   = 100       # C 단계 수

# ── 교차검증 설정 ──────────────────────────────────────────
N_SPLITS        = 5
CV_RANDOM_STATE = 42

# ── 분류기 설정 ────────────────────────────────────────────
RF_N_ESTIMATORS   = 200
XGB_N_ESTIMATORS  = 200

# ── 결과 테이블 컬럼 순서 ──────────────────────────────────
RESULT_COLUMNS = [
    "FS", "Classifier", "N_features",
    "Micro_Acc", "Macro_Acc",
    "Sens_정상", "Sens_경증", "Sens_중증", "Avg_Sens",
    "Avg_Spec",
    "ROC_AUC"
]

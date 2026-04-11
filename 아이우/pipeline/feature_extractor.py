"""
STEP 2-3: 전처리 + 피처 추출 (총 112개)
출력: results/features.csv
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import soundfile as sf
import librosa
import parselmouth
from parselmouth.praat import call

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *


# ──────────────────────────────────────────────────────────────
# 전처리: 안정구간 추출
# ──────────────────────────────────────────────────────────────

def load_audio(path):
    """wav 파일 로드. 스테레오면 모노 변환."""
    audio, sr = sf.read(path, always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = librosa.resample(audio.astype(float), orig_sr=sr, target_sr=TARGET_SR)
        sr = TARGET_SR
    return audio.astype(np.float64), sr


def extract_stable_segment(audio, sr):
    """
    앞뒤 10% 제거 → 중앙 80% 반환.
    MPT는 원본 전체 길이(초)로 별도 계산.
    """
    n = len(audio)
    mpt = n / sr                           # 원본 전체 길이 (초)
    start = int(n * (1 - STABLE_RATIO) / 2)
    end   = int(n * (1 - (1 - STABLE_RATIO) / 2))
    stable = audio[start:end]

    if len(stable) / sr < MIN_DURATION_SEC:
        return None, mpt, False            # 너무 짧으면 사용 불가

    return stable, mpt, True


# ──────────────────────────────────────────────────────────────
# A그룹: 발성 안정성 피처
# ──────────────────────────────────────────────────────────────

def _make_praat_objects(stable, sr):
    """Praat Sound / Pitch / PointProcess 공통 생성."""
    sound  = parselmouth.Sound(stable, sr)
    pitch  = call(sound, "To Pitch", 0, PITCH_FLOOR, PITCH_CEIL)
    pulses = call([sound, pitch], "To PointProcess (cc)")
    return sound, pitch, pulses


def extract_jitter(pulses):
    """Jitter 5종."""
    def safe_call(method):
        try:
            v = call(pulses, method, 0, 0,
                     JITTER_PERIOD_FLOOR, JITTER_PERIOD_CEIL, JITTER_MAX_FACTOR)
            return v if np.isfinite(v) else np.nan
        except Exception:
            return np.nan

    return {
        "jitter_local":    safe_call("Get jitter (local)"),
        "jitter_absolute": safe_call("Get jitter (local, absolute)"),
        "jitter_rap":      safe_call("Get jitter (rap)"),
        "jitter_ppq5":     safe_call("Get jitter (ppq5)"),
        "jitter_ddp":      safe_call("Get jitter (ddp)"),
    }


def extract_shimmer(sound, pulses):
    """Shimmer 6종."""
    def safe_call(method):
        try:
            v = call([sound, pulses], method, 0, 0,
                     JITTER_PERIOD_FLOOR, JITTER_PERIOD_CEIL,
                     JITTER_MAX_FACTOR, SHIMMER_MAX_AMPLITUDE)
            return v if np.isfinite(v) else np.nan
        except Exception:
            return np.nan

    return {
        "shimmer_local":  safe_call("Get shimmer (local)"),
        "shimmer_dB":     safe_call("Get shimmer (local_dB)"),
        "shimmer_apq3":   safe_call("Get shimmer (apq3)"),
        "shimmer_apq5":   safe_call("Get shimmer (apq5)"),
        "shimmer_apq11":  safe_call("Get shimmer (apq11)"),
        "shimmer_dda":    safe_call("Get shimmer (dda)"),
    }


def extract_hnr(sound):
    """HNR (Harmonics-to-Noise Ratio, dB)."""
    try:
        harm = call(sound, "To Harmonicity (cc)",
                    HNR_TIME_STEP, HNR_MIN_PITCH,
                    HNR_SILENCE_THRESH, HNR_PERIODS_PER_WIN)
        v = call(harm, "Get mean", 0, 0)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def extract_nhr(hnr_db):
    """
    NHR (Noise-to-Harmonics Ratio).
    HNR_dB = 10*log10(H/N) → NHR = N/(N+H) = 1/(10^(HNR/10)+1)
    """
    if hnr_db is None or not np.isfinite(hnr_db) or hnr_db <= -200:
        return np.nan
    hnr_linear = 10 ** (hnr_db / 10)
    return 1.0 / (hnr_linear + 1.0)


def extract_spi(sound, pitch):
    """
    SPI (Soft Phonation Index) = mean(H1 amp) / mean(H2 amp).
    Praat의 pitch를 이용해 기본 주파수 기반 harmonic 추출.
    """
    try:
        # 첫 번째 harmonic (H1) = F0 위치의 스펙트럼 에너지
        # 두 번째 harmonic (H2) = 2*F0 위치
        f0_mean = call(pitch, "Get mean", 0, 0, "Hertz")
        if not np.isfinite(f0_mean) or f0_mean <= 0:
            return np.nan

        spectrum = sound.to_spectrum()
        # 스펙트럼에서 H1, H2 주파수 대역의 평균 파워 추출
        bw = f0_mean * 0.4   # 각 harmonic 주변 ±40% 대역

        def band_power(center):
            lo, hi = center - bw/2, center + bw/2
            return call(spectrum, "Get band energy", lo, hi)

        h1 = band_power(f0_mean)
        h2 = band_power(2 * f0_mean)

        if h2 > 0 and np.isfinite(h1) and np.isfinite(h2):
            return h1 / h2
        return np.nan
    except Exception:
        return np.nan


def extract_group_A(stable, sr):
    """A그룹 전체 (14개) 반환. NaN은 이후 imputation."""
    sound, pitch, pulses = _make_praat_objects(stable, sr)
    hnr = extract_hnr(sound)
    result = {}
    result.update(extract_jitter(pulses))         # 5개
    result.update(extract_shimmer(sound, pulses)) # 6개
    result["hnr"]    = hnr                        # 1개
    result["nhr"]    = extract_nhr(hnr)           # 1개
    result["spi"]    = extract_spi(sound, pitch)  # 1개
    return result  # 14개 / 모음 → 3모음 합산 42개


# ──────────────────────────────────────────────────────────────
# B그룹: 조음 공간 피처 (원자 피처 + 유도 피처)
# ──────────────────────────────────────────────────────────────

def extract_formants_stats(stable, sr):
    """F1/F2 mean + SD 4개 추출."""
    try:
        sound = parselmouth.Sound(stable, sr)
        formant = call(sound, "To Formant (burg)", 0,
                       FORMANT_NUM, FORMANT_MAX_FORMANT,
                       FORMANT_WIN_LEN, FORMANT_PRE_EMPHASIS)
        duration = sound.duration
        times = np.arange(0.02, duration - 0.02, 0.01)

        f1_vals, f2_vals = [], []
        for t in times:
            v1 = call(formant, "Get value at time", 1, t, "Hertz", "Linear")
            v2 = call(formant, "Get value at time", 2, t, "Hertz", "Linear")
            if np.isfinite(v1) and v1 > 0: f1_vals.append(v1)
            if np.isfinite(v2) and v2 > 0: f2_vals.append(v2)

        def safe_stat(vals):
            if len(vals) < 3:
                return np.nan, np.nan
            return np.mean(vals), np.std(vals)

        f1_mean, f1_sd = safe_stat(f1_vals)
        f2_mean, f2_sd = safe_stat(f2_vals)
        return {"F1_mean": f1_mean, "F2_mean": f2_mean,
                "F1_SD": f1_sd,   "F2_SD": f2_sd}
    except Exception:
        return {"F1_mean": np.nan, "F2_mean": np.nan,
                "F1_SD": np.nan,  "F2_SD": np.nan}


def compute_vowel_space_features(formants):
    """
    VSA / FCR / VAI / F2이:F2우 — 3모음 동시 계산.

    Parameters
    ----------
    formants : dict
        keys: 'F1_mean_아', 'F2_mean_아', 'F1_mean_이', 'F2_mean_이',
              'F1_mean_우', 'F2_mean_우'
    """
    try:
        f1a = formants["F1_mean_아"]; f2a = formants["F2_mean_아"]
        f1i = formants["F1_mean_이"]; f2i = formants["F2_mean_이"]
        f1u = formants["F1_mean_우"]; f2u = formants["F2_mean_우"]

        vals = [f1a, f2a, f1i, f2i, f1u, f2u]
        if any(not np.isfinite(v) or v <= 0 for v in vals):
            return {"VSA": np.nan, "FCR": np.nan,
                    "VAI": np.nan, "F2이_F2우": np.nan}

        # VSA: 삼각형 면적 (Mou 2018)
        VSA = 0.5 * abs(
            (f1a * (f2i - f2u)) +
            (f1i * (f2u - f2a)) +
            (f1u * (f2a - f2i))
        )
        # FCR: Formant Centralization Ratio (Park 2020)
        FCR = (f2u + f2a + f1i + f1u) / (f2i + f1a)
        # VAI: Vowel Articulation Index
        VAI = (f2i + f1a) / (f1i + f1u + f2a + f2u)
        # F2이/F2우 비율
        F2_ratio = f2i / f2u

        return {"VSA": VSA, "FCR": FCR, "VAI": VAI, "F2이_F2우": F2_ratio}
    except Exception:
        return {"VSA": np.nan, "FCR": np.nan,
                "VAI": np.nan, "F2이_F2우": np.nan}


# ──────────────────────────────────────────────────────────────
# D그룹: F0 피처
# ──────────────────────────────────────────────────────────────

def extract_f0_stats(stable, sr):
    """F0 mean / SD / min / max 4개."""
    try:
        sound = parselmouth.Sound(stable, sr)
        pitch = call(sound, "To Pitch", F0_TIME_STEP, PITCH_FLOOR, PITCH_CEIL)
        times = np.arange(0, sound.duration, F0_TIME_STEP)
        f0_vals = []
        for t in times:
            v = call(pitch, "Get value at time", t, "Hertz", "Linear")
            if np.isfinite(v) and v > 0:
                f0_vals.append(v)
        if len(f0_vals) < 3:
            return {"F0_mean": np.nan, "F0_SD": np.nan,
                    "F0_min": np.nan,  "F0_max": np.nan}
        return {
            "F0_mean": np.mean(f0_vals),
            "F0_SD":   np.std(f0_vals),
            "F0_min":  np.min(f0_vals),
            "F0_max":  np.max(f0_vals),
        }
    except Exception:
        return {"F0_mean": np.nan, "F0_SD": np.nan,
                "F0_min": np.nan,  "F0_max": np.nan}


# ──────────────────────────────────────────────────────────────
# E그룹: MFCC
# ──────────────────────────────────────────────────────────────

def extract_mfcc(stable, sr):
    """MFCC 1~13 mean 13개."""
    try:
        mfcc = librosa.feature.mfcc(
            y=stable.astype(float), sr=sr,
            n_mfcc=N_MFCC, n_fft=N_FFT,
            hop_length=HOP_LENGTH, fmax=FMAX
        )
        return {f"MFCC_{i+1}": np.mean(mfcc[i]) for i in range(N_MFCC)}
    except Exception:
        return {f"MFCC_{i+1}": np.nan for i in range(N_MFCC)}


# ──────────────────────────────────────────────────────────────
# 세션 단위 피처 추출
# ──────────────────────────────────────────────────────────────

def extract_session_features(row, verbose=False):
    """
    단일 세션(3모음)에서 112개 피처 추출.

    Parameters
    ----------
    row : dict  — 'UID', 'path_아', 'path_이', 'path_우', '장애정도'
    """
    uid = row["UID"]
    features = {"UID": uid, "speaker_id": row["speaker_id"],
                "장애정도": row["장애정도"]}

    vowels = [("아", row["path_아"]),
              ("이", row["path_이"]),
              ("우", row["path_우"])]

    formant_means = {}   # VSA 등 유도 피처용

    for vowel, path in vowels:
        try:
            # --- 오디오 로드 ---
            audio, sr = load_audio(path)
            stable, mpt, ok = extract_stable_segment(audio, sr)

            # C그룹: MPT (원본 길이)
            features[f"MPT_{vowel}"] = mpt

            if not ok:
                if verbose:
                    print(f"  [WARN] {uid} /{vowel}/ stable segment 너무 짧음")
                # 해당 모음 피처 전부 NaN
                for k in _get_nan_keys(vowel):
                    features[k] = np.nan
                continue

            # A그룹 (14개)
            grp_a = extract_group_A(stable, sr)
            for k, v in grp_a.items():
                features[f"{k}_{vowel}"] = v

            # B그룹 원자 피처 (4개)
            grp_b = extract_formants_stats(stable, sr)
            for k, v in grp_b.items():
                features[f"{k}_{vowel}"] = v
                if "F1_mean" in k or "F2_mean" in k:
                    formant_means[f"{k}_{vowel}"] = v   # 유도 피처용

            # D그룹 (4개)
            grp_d = extract_f0_stats(stable, sr)
            for k, v in grp_d.items():
                features[f"{k}_{vowel}"] = v

            # E그룹 (13개)
            grp_e = extract_mfcc(stable, sr)
            for k, v in grp_e.items():
                features[f"{k}_{vowel}"] = v

        except Exception as e:
            if verbose:
                print(f"  [ERROR] {uid} /{vowel}/: {e}")
            for k in _get_nan_keys(vowel):
                features[k] = np.nan
            features[f"MPT_{vowel}"] = np.nan

    # B그룹 유도 피처 (4개): VSA / FCR / VAI / F2비율
    vowel_space = compute_vowel_space_features({
        "F1_mean_아": formant_means.get("F1_mean_아", np.nan),
        "F2_mean_아": formant_means.get("F2_mean_아", np.nan),
        "F1_mean_이": formant_means.get("F1_mean_이", np.nan),
        "F2_mean_이": formant_means.get("F2_mean_이", np.nan),
        "F1_mean_우": formant_means.get("F1_mean_우", np.nan),
        "F2_mean_우": formant_means.get("F2_mean_우", np.nan),
    })
    features.update(vowel_space)

    return features


def _get_nan_keys(vowel):
    """해당 모음 피처 키 목록 (NaN 채움용)."""
    keys = []
    # A: jitter 5 + shimmer 6 + hnr + nhr + spi = 14
    for p in ["jitter_local", "jitter_absolute", "jitter_rap",
              "jitter_ppq5", "jitter_ddp",
              "shimmer_local", "shimmer_dB", "shimmer_apq3",
              "shimmer_apq5", "shimmer_apq11", "shimmer_dda",
              "hnr", "nhr", "spi"]:
        keys.append(f"{p}_{vowel}")
    # B 원자: F1/F2 mean + SD = 4
    for p in ["F1_mean", "F2_mean", "F1_SD", "F2_SD"]:
        keys.append(f"{p}_{vowel}")
    # D: F0 4개
    for p in ["F0_mean", "F0_SD", "F0_min", "F0_max"]:
        keys.append(f"{p}_{vowel}")
    # E: MFCC 13개
    for i in range(1, 14):
        keys.append(f"MFCC_{i}_{vowel}")
    return keys


# ──────────────────────────────────────────────────────────────
# 배치 실행
# ──────────────────────────────────────────────────────────────

def run_feature_extraction(df_mapping, verbose=True):
    """
    전체 세션 피처 추출 후 DataFrame 반환.
    NaN은 train/test split 후 각 fold에서 imputation.
    """
    records = []
    n_total = len(df_mapping)

    for idx, row in df_mapping.iterrows():
        if verbose and idx % 10 == 0:
            print(f"  진행: {idx+1}/{n_total} — {row['UID']}")
        feat = extract_session_features(row.to_dict(), verbose=False)
        records.append(feat)

    df_feat = pd.DataFrame(records)

    # 피처 컬럼만 추출 (UID, speaker_id, 장애정도 제외)
    meta_cols = ["UID", "speaker_id", "장애정도"]
    feat_cols = [c for c in df_feat.columns if c not in meta_cols]

    if verbose:
        nan_counts = df_feat[feat_cols].isna().sum()
        print(f"\n  추출 완료: {len(df_feat)} 세션 × {len(feat_cols)} 피처")
        print(f"  NaN 있는 피처: {(nan_counts > 0).sum()}개")
        worst = nan_counts.nlargest(5)
        if worst.max() > 0:
            print(f"  NaN 많은 피처 Top5:\n{worst.to_string()}")

    return df_feat, feat_cols


if __name__ == "__main__":
    from pipeline.data_loader import load_mapping

    print("=== STEP 1: 데이터 매핑 ===")
    df_map = load_mapping(verbose=True)

    print("=== STEP 2-3: 피처 추출 ===")
    df_feat, feat_cols = run_feature_extraction(df_map, verbose=True)

    df_feat.to_csv(FEATURES_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {FEATURES_CSV}")
    print(f"피처 컬럼 (총 {len(feat_cols)}개):")
    for col in feat_cols:
        print(f"  {col}")

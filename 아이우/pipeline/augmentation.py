"""
파형 증강 모듈 (Train set 중증 전용)
- Pitch Shift ±1, ±1.5 semitone
- Additive Noise SNR 25dB
- Time Shift ±50ms, ±100ms
- KS-test 검증 (Jitter/Shimmer/HNR 분포 비교)
"""
import os, sys, warnings, tempfile
import numpy as np
import soundfile as sf
import librosa
from scipy.stats import ks_2samp

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *


# ──────────────────────────────────────────────────────────────
# 증강 함수 4종
# ──────────────────────────────────────────────────────────────

def aug_pitch_shift(audio, sr, semitones):
    """피치 시프트."""
    return librosa.effects.pitch_shift(
        audio.astype(float), sr=sr, n_steps=semitones
    )


def aug_add_noise(audio, sr, snr_db=25.0):
    """가산 백색 잡음 (SNR 지정)."""
    rms_signal = np.sqrt(np.mean(audio ** 2))
    rms_noise  = rms_signal / (10 ** (snr_db / 20))
    noise      = np.random.normal(0, rms_noise, len(audio))
    return (audio + noise).astype(np.float64)


def aug_time_shift(audio, sr, shift_ms):
    """시간 이동 (ms). 양수=앞으로, 음수=뒤로."""
    shift_samples = int(sr * shift_ms / 1000)
    if shift_samples >= 0:
        shifted = np.concatenate([audio[shift_samples:],
                                  np.zeros(shift_samples)])
    else:
        shifted = np.concatenate([np.zeros(-shift_samples),
                                  audio[:shift_samples]])
    return shifted.astype(np.float64)


# 증강 메서드 레지스트리
AUGMENTATION_METHODS = {
    "pitch_p1.0":  lambda a, sr: aug_pitch_shift(a, sr,  1.0),
    "pitch_p1.5":  lambda a, sr: aug_pitch_shift(a, sr,  1.5),
    "pitch_m1.0":  lambda a, sr: aug_pitch_shift(a, sr, -1.0),
    "pitch_m1.5":  lambda a, sr: aug_pitch_shift(a, sr, -1.5),
    "noise_25dB":  lambda a, sr: aug_add_noise(a, sr, snr_db=25.0),
    "tshift_p50":  lambda a, sr: aug_time_shift(a, sr,  50),
    "tshift_m50":  lambda a, sr: aug_time_shift(a, sr, -50),
    "tshift_p100": lambda a, sr: aug_time_shift(a, sr,  100),
    "tshift_m100": lambda a, sr: aug_time_shift(a, sr, -100),
}


# ──────────────────────────────────────────────────────────────
# KS-test 검증
# ──────────────────────────────────────────────────────────────

def _quick_features(audio, sr):
    """KS-test용 빠른 음향 피처 (Jitter 대용 ZCR / RMS / Centroid)."""
    import parselmouth
    from parselmouth.praat import call

    # 안정구간 추출
    n = len(audio)
    s = int(n * 0.10); e = int(n * 0.90)
    stable = audio[s:e]
    if len(stable) < sr * 0.3:
        stable = audio

    sound  = parselmouth.Sound(stable, sr)
    pitch  = call(sound, "To Pitch", 0, PITCH_FLOOR, PITCH_CEIL)
    pulses = call([sound, pitch], "To PointProcess (cc)")

    def safe(method, *args):
        try:
            v = call(*args, method, 0, 0,
                     JITTER_PERIOD_FLOOR, JITTER_PERIOD_CEIL, JITTER_MAX_FACTOR)
            return float(v) if np.isfinite(v) else np.nan
        except Exception:
            return np.nan

    jitter   = safe("Get jitter (local)", pulses)
    try:
        harm = call(sound, "To Harmonicity (cc)",
                    HNR_TIME_STEP, HNR_MIN_PITCH,
                    HNR_SILENCE_THRESH, HNR_PERIODS_PER_WIN)
        hnr = float(call(harm, "Get mean", 0, 0))
        hnr = hnr if np.isfinite(hnr) else np.nan
    except Exception:
        hnr = np.nan

    try:
        sh_args = [sound, pulses]
        shimmer = float(call(sh_args, "Get shimmer (local)", 0, 0,
                             JITTER_PERIOD_FLOOR, JITTER_PERIOD_CEIL,
                             JITTER_MAX_FACTOR, SHIMMER_MAX_AMPLITUDE))
        shimmer = shimmer if np.isfinite(shimmer) else np.nan
    except Exception:
        shimmer = np.nan

    return {"jitter": jitter, "shimmer": shimmer, "hnr": hnr}


def validate_augmentation_ks(orig_audios, aug_method_fn, sr, n_boot=1,
                               alpha=0.05, verbose=True, method_name=""):
    """
    KS-test: 원본 중증 오디오 vs 증강 오디오의 피처 분포 비교.
    p > alpha 이면 분포가 유의하게 다르지 않다 → OK

    Parameters
    ----------
    orig_audios  : list of np.ndarray  — 원본 중증 오디오
    aug_method_fn: callable(audio, sr) → augmented audio
    n_boot       : 오디오당 증강 횟수 (noise의 경우 여러 번 샘플링)

    Returns
    -------
    passed : bool  — True이면 이 증강 방법을 사용
    p_vals : dict  — 피처별 p-value
    """
    orig_feats = {"jitter": [], "shimmer": [], "hnr": []}
    aug_feats  = {"jitter": [], "shimmer": [], "hnr": []}

    for audio in orig_audios:
        f_orig = _quick_features(audio, sr)
        for k in orig_feats:
            if f_orig[k] is not None and np.isfinite(f_orig[k]):
                orig_feats[k].append(f_orig[k])

        for _ in range(n_boot):
            try:
                aug_audio = aug_method_fn(audio, sr)
                f_aug = _quick_features(aug_audio, sr)
                for k in aug_feats:
                    if f_aug[k] is not None and np.isfinite(f_aug[k]):
                        aug_feats[k].append(f_aug[k])
            except Exception:
                pass

    p_vals = {}
    all_pass = True
    for k in ["jitter", "shimmer", "hnr"]:
        o, a = orig_feats[k], aug_feats[k]
        if len(o) < 2 or len(a) < 2:
            p_vals[k] = np.nan
            continue
        stat, p = ks_2samp(o, a)
        p_vals[k] = p
        if p < alpha:
            all_pass = False

    if verbose:
        status = "✅ PASS" if all_pass else "❌ FAIL"
        pstr = " | ".join(f"{k}:p={v:.3f}" for k, v in p_vals.items()
                          if not np.isnan(v))
        print(f"    KS-test [{method_name}]: {status}  ({pstr})")

    return all_pass, p_vals


# ──────────────────────────────────────────────────────────────
# 배치 증강 + 검증
# ──────────────────────────────────────────────────────────────

def augment_severe_sessions(train_df, verbose=True):
    """
    Training set의 중증(장애정도==2) 세션을 증강.
    KS-test 통과한 방법만 사용.

    Returns
    -------
    aug_df : pd.DataFrame  — 증강 세션 목록 (매핑 형식)
    passed_methods : list  — KS-test 통과한 증강 방법명
    """
    import pandas as pd, tempfile, uuid

    severe_train = train_df[train_df["장애정도"] == 2].reset_index(drop=True)
    if len(severe_train) == 0:
        if verbose: print("  [WARN] 훈련셋에 중증 샘플 없음 → 증강 불가")
        return pd.DataFrame(), []

    if verbose:
        print(f"\n[증강] 중증 훈련 세션: {len(severe_train)}개")

    # ── 1. 각 세션에서 3모음 오리지널 오디오 로드
    orig_per_session = []
    sr_global = TARGET_SR
    for _, row in severe_train.iterrows():
        session_audios = {}
        for vowel, path_col in [("아", "path_아"), ("이", "path_이"), ("우", "path_우")]:
            try:
                import soundfile as sf
                audio, sr = sf.read(row[path_col], always_2d=False)
                if audio.ndim == 2: audio = audio.mean(axis=1)
                if sr != TARGET_SR:
                    audio = librosa.resample(audio.astype(float),
                                             orig_sr=sr, target_sr=TARGET_SR)
                session_audios[vowel] = audio.astype(np.float64)
                sr_global = TARGET_SR
            except Exception as e:
                if verbose: print(f"    [WARN] {row['UID']} /{vowel}/ 로드 실패: {e}")
                session_audios[vowel] = None
        orig_per_session.append((row, session_audios))

    # ── 2. KS-test: /아/ 기준으로 증강 방법 검증
    all_a_audios = [s["아"] for _, s in orig_per_session
                    if s.get("아") is not None]

    if verbose:
        print(f"\n  KS-test 검증 ({len(all_a_audios)}개 원본 /아/ 기준):")

    passed_methods = []
    for m_name, m_fn in AUGMENTATION_METHODS.items():
        try:
            ok, _ = validate_augmentation_ks(
                all_a_audios, m_fn, sr_global,
                n_boot=1, alpha=0.05,
                verbose=verbose, method_name=m_name
            )
            if ok:
                passed_methods.append(m_name)
        except Exception as ex:
            if verbose: print(f"    [ERROR] {m_name}: {ex}")

    if verbose:
        print(f"\n  KS-test 통과 방법: {passed_methods}")
        if not passed_methods:
            print("  [WARN] 통과 방법 없음 → noise_25dB 강제 사용")
            passed_methods = ["noise_25dB"]

    # ── 3. 통과된 방법으로 증강 세션 생성 (임시 wav 파일)
    aug_dir = os.path.join(BASE_DIR, "results", "aug_wavs")
    os.makedirs(aug_dir, exist_ok=True)

    aug_records = []
    for row, session_audios in orig_per_session:
        for m_name in passed_methods:
            m_fn = AUGMENTATION_METHODS[m_name]
            aug_paths = {}
            all_ok = True
            for vowel in ["아", "이", "우"]:
                orig_audio = session_audios.get(vowel)
                if orig_audio is None:
                    aug_paths[vowel] = None
                    continue
                try:
                    aug_audio = m_fn(orig_audio, sr_global)
                    fname = f"{row['UID']}_{m_name}_{vowel}.wav"
                    fpath = os.path.join(aug_dir, fname)
                    import soundfile as sf
                    sf.write(fpath, aug_audio, sr_global, subtype="PCM_16")
                    aug_paths[vowel] = fpath
                except Exception as ex:
                    if verbose: print(f"    [WARN] {row['UID']} {m_name} /{vowel}/: {ex}")
                    all_ok = False; break

            has_aug = any(p is not None for p in aug_paths.values())
            if all_ok and has_aug:
                aug_records.append({
                    "UID":        f"{row['UID']}_{m_name}",
                    "speaker_id": row["speaker_id"],  # 원본 화자ID 유지
                    "장애정도":  2,
                    "path_아":   aug_paths["아"],
                    "path_이":   aug_paths["이"],
                    "path_우":   aug_paths["우"],
                    "is_augmented": True,
                })

    import pandas as pd
    aug_df = pd.DataFrame(aug_records)
    if verbose:
        print(f"\n  총 증강 세션: {len(aug_df)}개 "
              f"(원본 {len(severe_train)}개 × {len(passed_methods)}방법)")
    return aug_df, passed_methods


if __name__ == "__main__":
    print("이 모듈은 run_augmented.py에서 호출됩니다.")

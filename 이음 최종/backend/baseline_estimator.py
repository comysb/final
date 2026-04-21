import numpy as np
import librosa
from typing import Dict, Any, Optional

def estimate_noise_floor(envelope_array: np.ndarray, time_axis: np.ndarray = None, method: str = "percentile") -> float:
    """하위 10% 기반 또는 무음 구간 기반 노이즈 플로어 추정"""
    if len(envelope_array) == 0:
        return -50.0 # Extreme fallback fallback
        
    if method == "percentile":
        return float(np.nanpercentile(envelope_array, 10))
    elif method == "initial":
        # 초기 0.5초를 기준으로 삼음 (onset이 없다는 가정)
        if time_axis is not None and len(time_axis) > 0:
            init_mask = time_axis <= 0.5
            if np.any(init_mask):
                return float(np.nanmean(envelope_array[init_mask]))
        return float(np.nanpercentile(envelope_array, 10))
    
    return float(np.nanpercentile(envelope_array, 10))

def estimate_baseline_f0(f0_array: np.ndarray, time_axis: np.ndarray = None, voiced_mask: np.ndarray = None) -> Optional[float]:
    """초기 안정 발성 구간 기반 F0 기준값 추정"""
    if voiced_mask is None:
        voiced_mask = f0_array > 0
        
    valid_f0 = f0_array[voiced_mask]
    if len(valid_f0) == 0:
        return None
        
    # 이상적으로 첫 1~2초 사이의 안정적 구간 중 가장 긴 구간 이용 등 고도화 가능
    # 여기서는 단순 Voiced 중앙값으로 대체 추정 (추후 보완)
    return float(np.nanmedian(valid_f0))

def estimate_baseline_loudness(L_array: np.ndarray, time_axis: np.ndarray = None, voiced_mask: np.ndarray = None) -> Optional[float]:
    """기준 소음 대비 평균 음량 도출"""
    if voiced_mask is None or not np.any(voiced_mask):
        if len(L_array) == 0:
            return None
        return float(np.nanmedian(L_array))
        
    return float(np.nanmean(L_array[voiced_mask]))

def _align_time_axis(source_array: np.ndarray, source_time: np.ndarray, target_time: np.ndarray) -> np.ndarray:
    """간이 배열 보간용 내부 유틸. 경계를 벗어나면 NaN으로 처리하여 불필요한 평균 왜곡 방지."""
    if len(source_array) == 0 or len(source_time) == 0 or len(target_time) == 0:
        return np.full_like(target_time, fill_value=np.nan, dtype=float)
    
    # Strictly increasing check 유연화: target_time이 중복일 수 있으므로
    if not np.all(np.diff(target_time) >= 0) or len(target_time) < 2:
        return np.full_like(target_time, fill_value=np.nan, dtype=float)
        
    if not np.all(np.diff(source_time) >= 0):
        return np.full_like(target_time, fill_value=np.nan, dtype=float)
        
    return np.interp(target_time, source_time, source_array, left=np.nan, right=np.nan)

def extract_baseline_features(audio_path: str, duration: float = 3.0, mode: str = "session") -> Dict[str, Any]:
    """세션 단위의 캘리브레이션 딕셔너리를 반환합니다."""
    # (실제 구현에서는 acoustic_utils를 사용해 피처를 뽑고 추정합니다만 모듈 임포트 방지 위해 지연 로드 사용 가능)
    import acoustic_utils as utils
    
    f0_raw = utils.extract_pitch_track(audio_path)
    L_raw = utils.extract_intensity_track(audio_path)
    env_raw = utils.extract_breath_envelope(audio_path)
    
    # Duration Slicing 반영
    f0 = f0_raw.get("f0_array", np.array([]))
    f0_time = f0_raw.get("time_axis", np.array([]))
    if len(f0_time) > 0:
        slice_mask = f0_time <= duration
        f0 = f0[slice_mask]
        f0_time = f0_time[slice_mask]
        
    v_mask = f0 > 0 if len(f0) > 0 else np.array([])
    
    L_array_full = L_raw.get("L_array", np.array([]))
    L_time_full = L_raw.get("time_axis", np.array([]))
    
    # 시간축 불일치 방지 (F0 시간축 기준으로 병합)
    l_arr_aligned = _align_time_axis(L_array_full, L_time_full, f0_time)
    
    e_arr = env_raw.get("envelope_array", np.array([]))
    e_time = env_raw.get("time_axis", np.array([]))
    if len(e_time) > 0:
        slice_mask_e = e_time <= duration
        e_arr = e_arr[slice_mask_e]
        e_time = e_time[slice_mask_e]
    
    base_f0 = estimate_baseline_f0(f0, voiced_mask=v_mask)
    base_L = estimate_baseline_loudness(l_arr_aligned, voiced_mask=v_mask)
    n_floor = estimate_noise_floor(e_arr, time_axis=e_time)
    
    from rehab_evaluator import QualityFlag
    
    # 퀄리티 판별
    success = True
    q_flag = QualityFlag.OK
    
    # None 체크 및 NaN 체킹 병행
    if base_f0 is None or base_L is None or np.isnan(base_f0) or np.isnan(base_L):
        q_flag = QualityFlag.INSUFFICIENT_VOICED
        base_f0 = 100.0 if (base_f0 is None or np.isnan(base_f0)) else base_f0
        base_L = 50.0 if (base_L is None or np.isnan(base_L)) else base_L

    return {
        "success": success,
        "quality_flag": q_flag,
        "baseline_f0": base_f0,
        "baseline_loudness": base_L,
        "noise_floor": n_floor if not np.isnan(n_floor) else -50.0,
        "voiced_ratio": float(np.mean(v_mask)) if len(v_mask) > 0 else 0.0,
        "source": mode
    }


def extract_baseline_features_from_array(
    audio_array: np.ndarray,
    sr: int = 16000,
    duration: float = 3.0,
) -> dict:
    """세션 캘리브레이션용: numpy 배열로 baseline 추출.

    반환 스키마는 extract_baseline_features(audio_path)와 완전히 동일합니다.
    rehab_pipeline.py의 _ensure_baseline()이 두 함수를 구분 없이 사용할 수 있게
    success / quality_flag / voiced_ratio / source 필드를 모두 포함합니다.
    """
    import acoustic_utils as utils
    from rehab_evaluator import QualityFlag

    # duration 슬라이싱: 첫 N초만 사용하여 안정된 구간 baseline 추정
    n_samples = int(duration * sr)
    clipped = audio_array[:n_samples] if len(audio_array) > n_samples else audio_array

    f0_data  = utils.extract_pitch_track_from_array(clipped, sr)
    L_data   = utils.extract_intensity_track_from_array(clipped, sr)
    env_data = utils.extract_breath_envelope_from_array(clipped, sr)

    f0_arr   = f0_data.get("f0_array", np.array([]))
    f0_time  = f0_data.get("time_axis", np.array([]))
    L_arr    = L_data.get("L_array", np.array([]))
    L_time   = L_data.get("time_axis", np.array([]))
    e_arr    = env_data.get("envelope_array", np.array([]))
    e_time   = env_data.get("time_axis", np.array([]))

    v_mask = f0_arr > 0 if len(f0_arr) > 0 else np.array([], dtype=bool)

    # 시간축 불일치 방지: L 배열을 f0 시간축 기준으로 정렬
    l_aligned = _align_time_axis(L_arr, L_time, f0_time) if (len(L_arr) > 0 and len(f0_time) > 0) else L_arr

    base_f0 = estimate_baseline_f0(f0_arr, voiced_mask=v_mask)
    base_L  = estimate_baseline_loudness(l_aligned, voiced_mask=v_mask)
    n_floor = estimate_noise_floor(e_arr, time_axis=e_time)

    success = True
    q_flag  = QualityFlag.OK

    if base_f0 is None or np.isnan(base_f0):
        q_flag  = QualityFlag.INSUFFICIENT_VOICED
        base_f0 = 100.0
    if base_L is None or np.isnan(base_L):
        q_flag  = QualityFlag.INSUFFICIENT_VOICED
        base_L  = 50.0

    return {
        "success": success,
        "quality_flag": q_flag,
        "baseline_f0": base_f0,
        "baseline_loudness": base_L,
        "noise_floor": n_floor if not np.isnan(n_floor) else -50.0,
        "voiced_ratio": float(np.mean(v_mask)) if len(v_mask) > 0 else 0.0,
        "source": "array_calibration",
    }


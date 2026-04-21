import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class EvaluatorConfig:
    min_db_threshold: float = -30.0 # dBFS 기준 호흡 최소 감지 레벨 
    pitch_tolerance_cents: float = 50.0
    voiced_min_ratio: float = 0.4
    f0_jump_threshold_ratio: float = 1.8
    median_filter_kernel: int = 5
    loudness_target_gain_db: float = 6.0
    pitch_target_ratio: float = 1.10
    hz_tolerance: float = 5.0 # For pitch drift absolute hz

class ValidityFlag:
    OK = "ok"
    DEGRADED = "degraded"
    INVALID = "invalid"

class QualityFlag:
    OK = "ok"
    DEGRADED = "degraded"
    INSUFFICIENT_VOICED = "insufficient_voiced"
    UNSTABLE_EXTRACTION = "unstable_extraction"
    LOW_SNR = "low_snr"
    MISALIGNED_TIME_AXIS = "misaligned_time_axis"
    INVALID = "invalid"

class RehabAudioEvaluator:
    def __init__(self, config: EvaluatorConfig, sample_rate: int = 16000):
        self.config = config
        self.sr = sample_rate

    def _build_result(self, task_name: str, success: bool, validity_flag: str, 
                      quality_flag: str, metrics: Dict[str, Any], debug: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        모든 평가 과제의 공통 반환 스키마 구성 유틸리티.
        """
        has_nan = any(isinstance(v, (float, np.floating)) and np.isnan(v) for v in metrics.values())
        if has_nan:
            validity_flag = ValidityFlag.INVALID
            if quality_flag == QualityFlag.OK:
                quality_flag = QualityFlag.INVALID

        # JSON 직렬화를 위해 NaN 값은 0.0으로 치환하고 numpy float타입은 내장 float으로 캐스팅
        clean_metrics = {}
        for k, v in metrics.items():
            if isinstance(v, (float, np.floating)):
                if np.isnan(v):
                    clean_metrics[k] = 0.0
                else:
                    clean_metrics[k] = float(v)
            else:
                clean_metrics[k] = v

        return {
            "task_name": task_name,
            "success": success if not has_nan else False,
            "validity_flag": validity_flag,
            "quality_flag": quality_flag,
            "metrics": clean_metrics,
            "debug": debug or {}
        }

    def _quality_gate(self, valid_ratio: float, extra_flags: str = None) -> str:
        """Voiced 비율 등에 따라 신뢰 등급 판단 (고정 플래그 셋 사용)."""
        if extra_flags:
            return extra_flags
        if valid_ratio >= 0.7:
            return QualityFlag.OK
        elif valid_ratio >= self.config.voiced_min_ratio:
            return QualityFlag.DEGRADED
        return QualityFlag.INSUFFICIENT_VOICED

    def _align_array(self, source_array: np.ndarray, source_time: np.ndarray, target_time: np.ndarray) -> np.ndarray:
        """source_array를 target_time 기준축으로 선형 보간하여 배열 길이 및 매칭을 수행. 범위 외측은 NaN 처리."""
        if len(source_array) == 0 or len(source_time) == 0 or len(target_time) == 0:
            return np.full_like(target_time, fill_value=np.nan, dtype=float)
            
        if not np.all(np.diff(target_time) >= 0) or len(target_time) < 2:
            return np.full_like(target_time, fill_value=np.nan, dtype=float)
            
        if not np.all(np.diff(source_time) >= 0):  # 보수적인 Source Time 단조 검증
            return np.full_like(target_time, fill_value=np.nan, dtype=float)
            
        return np.interp(target_time, source_time, source_array, left=np.nan, right=np.nan)

    def _smooth_f0(self, f0_array: np.ndarray) -> Dict[str, Any]:
        """F0 시계열 보정 (Unvoiced 제거, Outlier 보정, Median Filter)"""
        voiced_mask = f0_array > 0
        valid_ratio = float(np.mean(voiced_mask))
        num_valid_frames = int(np.sum(voiced_mask))
        
        f0_smooth = np.copy(f0_array)
        octave_jump_count = 0
        
        if num_valid_frames < 2:
            return {
                "f0_smooth": f0_smooth, "voiced_mask": voiced_mask, "valid_ratio": valid_ratio,
                "num_valid_frames": num_valid_frames, "num_total_frames": len(f0_array),
                "octave_jump_count": 0, "quality_flag": QualityFlag.INSUFFICIENT_VOICED
            }
            
        import scipy.signal
        
        # 발성 구간에 대하여 Median Filtering 수행 (Outlier 완화)
        kernel_size = min(self.config.median_filter_kernel, num_valid_frames)
        if kernel_size % 2 == 0: kernel_size -= 1
        if kernel_size >= 3:
            f0_smooth[voiced_mask] = scipy.signal.medfilt(f0_smooth[voiced_mask], kernel_size=kernel_size)
        
        # Octave jump (Pitch Double/Half) 로컬 Median 기준 보정
        valid_indices = np.where(voiced_mask)[0]
        val_f0 = f0_smooth[valid_indices]
        
        for i in range(len(val_f0)):
            local_med = np.median(val_f0[max(0, i-2) : min(len(val_f0), i+3)])
            r = val_f0[i] / (local_med + 1e-6)
            
            if r > self.config.f0_jump_threshold_ratio:
                val_f0[i] /= 2.0
                octave_jump_count += 1
            elif r < (1.0 / self.config.f0_jump_threshold_ratio):
                val_f0[i] *= 2.0
                octave_jump_count += 1
        
        f0_smooth[valid_indices] = val_f0
        
        # 무성구간(NaN 처리될 부분)을 보간하여 끊김 없는 미분을 위한 선형 보간
        all_indices = np.arange(len(f0_array))
        f0_smooth = np.interp(all_indices, valid_indices, f0_smooth[valid_indices])

        return {
            "f0_smooth": f0_smooth,
            "voiced_mask": voiced_mask,
            "valid_ratio": valid_ratio,
            "num_valid_frames": num_valid_frames,
            "num_total_frames": len(f0_array),
            "octave_jump_count": octave_jump_count,
            "quality_flag": self._quality_gate(valid_ratio)
        }

    # ==========================================
    # 1. 호흡 / 발성 평가
    # ==========================================
    def eval_breathing_proxy(self, envelope_array: np.ndarray, time_axis: np.ndarray) -> Dict[str, Any]:
        """3. 호흡운동 (Proxy)"""
        if len(envelope_array) == 0:
            return self._build_result("breathing_proxy", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})
        
        # 1. Threshold crossing
        db_threshold = self.config.min_db_threshold
        exhale_mask = envelope_array > db_threshold
        
        if not np.any(exhale_mask):
            return self._build_result("breathing_proxy", True, ValidityFlag.DEGRADED, QualityFlag.LOW_SNR, 
                                      {"estimated_exhale_duration": 0.0, "breath_stability": 0.0})

        # 가장 긴 호기 구간 찾기 (연속된 참 값의 최대 길이)
        exhale_ints = exhale_mask.astype(int)
        runs = np.split(exhale_ints, np.where(np.diff(exhale_ints) != 0)[0] + 1)
        longest_run = max([len(r) for r in runs if r[0] == 1], default=0)
        
        time_step = time_axis[1] - time_axis[0] if len(time_axis) > 1 else 0.01
        est_duration = longest_run * time_step
        
        # 안정도(Stability) = CV, dB 평균 이슈 방지를 위해 Linear 스케일 엠플리튜드로 변환 후 연산
        valid_envelope = envelope_array[exhale_mask]
        linear_env = 10 ** (valid_envelope / 20.0)
        cv = np.std(linear_env) / (np.mean(linear_env) + 1e-6)
        stability = max(0.0, 1.0 - cv)

        metrics = {
            "estimated_exhale_duration": est_duration,
            "breath_stability": stability
        }
        return self._build_result("breathing_proxy", True, ValidityFlag.OK, QualityFlag.OK, metrics)

    def eval_sustained_phonation(self, voiced_mask: np.ndarray, L_array: np.ndarray, F0_array: np.ndarray, time_axis: np.ndarray, intensity_time_axis: np.ndarray, target_duration: Optional[float] = None) -> Dict[str, Any]:
        """4. 지속발성"""
        if len(voiced_mask) == 0 or not np.any(voiced_mask):
            return self._build_result("sustained_phonation", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})

        valid_ratio = np.mean(voiced_mask)
        q_flag = self._quality_gate(valid_ratio)
        if q_flag == QualityFlag.INSUFFICIENT_VOICED:
            return self._build_result("sustained_phonation", True, ValidityFlag.INVALID, q_flag, {})

        time_step = time_axis[1] - time_axis[0] if len(time_axis) > 1 else 0.01
        
        # 가장 긴 발성 구간
        voiced_ints = voiced_mask.astype(int)
        runs = np.split(voiced_ints, np.where(np.diff(voiced_ints) != 0)[0] + 1)
        longest_run = max([len(r) for r in runs if r[0] == 1], default=0)
        max_duration = longest_run * time_step
        
        # CV 계산 (길이 불일치를 방지하기 위한 Align 배열 보간)
        L_aligned = self._align_array(L_array, intensity_time_axis, time_axis)
        
        valid_L = L_aligned[voiced_mask]
        loudness_cv = np.std(valid_L) / (np.mean(valid_L) + 1e-6) if len(valid_L) > 0 else 0.0
        
        valid_F0 = F0_array[voiced_mask]
        pitch_cv = np.std(valid_F0) / (np.mean(valid_F0) + 1e-6) if len(valid_F0) > 0 else 0.0

        success = True
        if target_duration is not None:
            success = (max_duration >= target_duration)

        metrics = {
            "max_duration": max_duration,
            "voiced_ratio": valid_ratio,
            "loudness_cv": loudness_cv,
            "pitch_cv": pitch_cv
        }
        return self._build_result("sustained_phonation", success, ValidityFlag.OK, q_flag, metrics)

    def eval_pitch_glide(self, f0_array: np.ndarray, time_axis: np.ndarray, direction: str = "up", target_change_percent: Optional[float] = None, ref_trajectory: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """5, 6. 음도올리기/내리기 통합"""
        smooth_res = self._smooth_f0(f0_array)
        f0_smooth = smooth_res["f0_smooth"]
        voiced_mask = smooth_res["voiced_mask"]
        
        if smooth_res["quality_flag"] == QualityFlag.INSUFFICIENT_VOICED:
            return self._build_result("pitch_glide", True, ValidityFlag.INVALID, smooth_res["quality_flag"], {})

        valid_f0 = f0_smooth[voiced_mask]
        if len(valid_f0) < 2:
            return self._build_result("pitch_glide", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})

        # 미분: np.gradient
        df0_dt = np.gradient(valid_f0)
        
        if direction == "up":
            monotonic_frames = np.sum(df0_dt >= -0.5) # 약간의 오차 허용 (-epsilon)
            range_reached = np.max(valid_f0) - valid_f0[0]
        else:
            monotonic_frames = np.sum(df0_dt <= 0.5)
            range_reached = valid_f0[0] - np.min(valid_f0)

        monotonicity_rate = monotonic_frames / len(valid_f0)
        
        baseline_f0 = valid_f0[0]
        change_percent = (range_reached / baseline_f0 * 100.0) if baseline_f0 > 0 else 0.0

        success = True
        if target_change_percent is not None:
            success = (change_percent >= target_change_percent)

        # 목표 궤적 오차 연산
        traj_error = 0.0
        if ref_trajectory is not None and len(ref_trajectory) == len(f0_smooth):
            diff = np.abs(f0_smooth[voiced_mask] - ref_trajectory[voiced_mask])
            traj_error = np.mean(diff)

        metrics = {
            "trajectory_error": traj_error,
            "monotonicity_rate": monotonicity_rate,
            "range_reached": range_reached,
            "change_percent": change_percent,
            "f0_start": valid_f0[0],
            "f0_end": valid_f0[-1]
        }
        return self._build_result("pitch_glide", success, ValidityFlag.OK, smooth_res["quality_flag"], metrics)

    def eval_pitch_control(self, F0_array: np.ndarray, time_axis: np.ndarray, baseline_F0: float, target_ratio: float, hz_tolerance: float = 5.0) -> Dict[str, Any]:
        """7. 피치조절"""
        smooth_res = self._smooth_f0(F0_array)
        f0_smooth = smooth_res["f0_smooth"]
        voiced_mask = smooth_res["voiced_mask"]
        
        if smooth_res["quality_flag"] == QualityFlag.INSUFFICIENT_VOICED:
            return self._build_result("pitch_control", True, ValidityFlag.INVALID, smooth_res["quality_flag"], {})

        target_pitch = baseline_F0 * target_ratio

        valid_f0 = f0_smooth[voiced_mask]
        if len(valid_f0) == 0:
            return self._build_result("pitch_control", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})

        pitch_ok_mask = np.abs(valid_f0 - target_pitch) <= hz_tolerance
        pitch_accuracy = np.mean(pitch_ok_mask)
        pitch_error_mean = float(np.mean(np.abs(valid_f0 - target_pitch)))

        # 가장 긴 유지 시간
        time_step = time_axis[1] - time_axis[0] if len(time_axis) > 1 else 0.01
        ok_ints = pitch_ok_mask.astype(int)
        runs = np.split(ok_ints, np.where(np.diff(ok_ints) != 0)[0] + 1)
        longest_run = max([len(r) for r in runs if r[0] == 1], default=0)
        max_hold_time = longest_run * time_step

        metrics = {
            "pitch_accuracy": pitch_accuracy, 
            "pitch_error_mean": pitch_error_mean, 
            "max_hold_time": max_hold_time
        }
        return self._build_result("pitch_control", True, ValidityFlag.OK, smooth_res["quality_flag"], metrics)

    def eval_loudness_control(self, L_array: np.ndarray, time_axis: np.ndarray, baseline_L: float, target_gain_db: float) -> Dict[str, Any]:
        """8. 볼륨업"""
        if len(L_array) == 0:
            return self._build_result("loudness_control", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})

        target_loudness = baseline_L + target_gain_db
        L_ok_mask = L_array >= target_loudness
        loudness_target_rate = float(np.mean(L_ok_mask))
        max_loudness = float(np.max(L_array))
        mean_loudness = float(np.mean(L_array))

        metrics = {
            "loudness_target_rate": loudness_target_rate, 
            "max_loudness": max_loudness, 
            "mean_loudness": mean_loudness
        }
        return self._build_result("loudness_control", True, ValidityFlag.OK, QualityFlag.OK, metrics)

    def eval_glottal_closure(self, hnr: float, cpp: Optional[float], jitter: float, shimmer: float, L_array: np.ndarray, onset_time: float) -> Dict[str, Any]:
        """9. 성문폐쇄"""
        q_flag = QualityFlag.OK
        
        # CPP가 결측되었을 경우 백업 (Fallback)
        if cpp is None or np.isnan(cpp):
            q_flag = QualityFlag.UNSTABLE_EXTRACTION
            closure_quality_score = (-jitter * 200 - shimmer * 100) + hnr
        else:
            closure_quality_score = (cpp * 0.5 + hnr * 0.5)
        
        attack_time = onset_time # 프롬프트 자극 후 소리가 터져나오기까지의 delay
        
        metrics = {
            "closure_quality_score": float(closure_quality_score), 
            "attack_time": float(attack_time)
        }
        debug = {"cpp_missing": bool(cpp is None or np.isnan(cpp))}
        return self._build_result("glottal_closure", True, ValidityFlag.OK, q_flag, metrics, debug=debug)

    # ==========================================
    # 2. 발음 / 말하기 평가
    # ==========================================
    def eval_contrast_drills(self, logits_matrix: np.ndarray, target_idx: int, confusion_idx: int, alignment_score: Optional[float] = None, target_segments: Optional[Dict] = None) -> Dict[str, Any]:
        """#10. 대조훈련 (Contrast Drills)
        
        음소 대조 훈련: logits_matrix에서 target 음소와 confusion 음소의
        posterior 확률 차이(margin)를 계산하여 구별 성공 여부를 판단한다.
        
        Args:
            logits_matrix:   ASR 모델 출력 logits (frames × vocab_size)
            target_idx:      목표 음소의 vocab 인덱스
            confusion_idx:   혼동 음소의 vocab 인덱스
            alignment_score: (선택) 외부 정렬 신뢰도 점수
            target_segments: (선택) 분석할 구간 {"start": float, "end": float} (초 단위)
        
        Returns:
            _build_result() 스키마 결과 dict
        
        TODO(Phase 3): alignment_service.py 연동으로 logits/segment 자동 생성 예정
        """
        # Logits -> Softmax
        exp_logits = np.exp(logits_matrix - np.max(logits_matrix, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
        
        # 특정 구간 정보가 있으면 그 구간의 평균 확률 계산
        if target_segments:
            start_f = int(target_segments["start"] * 50) # wav2vec2 50Hz frame rate assumption
            end_f = int(target_segments["end"] * 50)
            probs = probs[start_f:end_f]
            
        mean_target_prob = float(np.mean(probs[:, target_idx]))
        mean_confuse_prob = float(np.mean(probs[:, confusion_idx]))
        posterior_margin = mean_target_prob - mean_confuse_prob
        
        contrast_success = posterior_margin > 0.05
        
        metrics = {
            "posterior_margin": posterior_margin, 
            "contrast_success": contrast_success,
            "mean_target_prob": mean_target_prob,
            "mean_confusion_prob": mean_confuse_prob
        }
        return self._build_result("contrast_drills", contrast_success, ValidityFlag.OK, QualityFlag.OK, metrics)

    def eval_ddk_hybrid(self, onset_times: List[float], target_rate: Optional[float] = None, predicted_sequence: Optional[List[str]] = None, target_sequence: Optional[List[str]] = None, alignment_segments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """#12. DDK 직접훈련 (Diadochokinesis)"""
        if len(onset_times) < 2:
            return self._build_result("ddk_hybrid", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})
            
        # 타격 속도 및 리듬 안정도 (Onset 기반)
        intervals = np.diff(onset_times)
        repetition_rate = len(onset_times) / (onset_times[-1] - onset_times[0]) if (onset_times[-1] - onset_times[0]) > 0 else 0
        rhythm_stability = 1.0 - (np.std(intervals) / (np.mean(intervals) + 1e-6))
        
        sequence_accuracy = 0.0
        if predicted_sequence and target_sequence:
            import difflib
            # 목표 순서 배열과 실제 인식된 배열 간의 유사성 비율
            sm = difflib.SequenceMatcher(None, predicted_sequence, target_sequence)
            sequence_accuracy = float(sm.ratio())
            
        success = True
        if target_rate is not None:
            success = (repetition_rate >= target_rate)

        metrics = {
            "repetition_rate": float(repetition_rate), 
            "rhythm_stability": max(0.0, float(rhythm_stability)), 
            "sequence_accuracy": sequence_accuracy, 
            "pause_ratio": 0.0
        }
        debug = {"sequence_source": "alignment" if alignment_segments else "onset_only", "onset_count": len(onset_times)}
        return self._build_result("ddk_hybrid", success, ValidityFlag.OK, QualityFlag.OK, metrics, debug)

    def eval_stress_contrast(self, L_array: np.ndarray, F0_array: np.ndarray, time_axis: np.ndarray, word_timestamps: List[Dict], target_word_idx: int) -> Dict[str, Any]:
        """#11. 대립강세 (Contrastive Stress)
        
        단어 수준 강세 대비 훈련: 음량(L), 기본주파수(F0), 지속시간(dur)을
        Z-score로 정규화한 뒤 합산하여 목표 단어가 가장 강세를 받았는지 판단한다.
        
        Args:
            L_array:         강도(dB) 배열
            F0_array:        기본주파수(Hz) 배열
            time_axis:       공통 시간축 (L/F0와 동일 해상도)
            word_timestamps: 단어별 타이밍 [{"word": str, "start": float, "end": float}, ...]
            target_word_idx: 강세 목표 단어 인덱스
        
        Returns:
            _build_result() 스키마 결과 dict
        
        TODO(Phase 3): alignment_service.py 연동으로 word_timestamps 자동 생성 예정
        """
        if not word_timestamps or len(word_timestamps) <= target_word_idx:
            return self._build_result("stress_contrast", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})
            
        word_metrics = []
        for word_info in word_timestamps:
            start_t, end_t = word_info["start"], word_info["end"]
            mask = (time_axis >= start_t) & (time_axis <= end_t)
            
            w_L = np.mean(L_array[mask]) if np.any(mask) else 0.0
            w_F0 = np.mean(F0_array[mask]) if np.any(mask) else 0.0
            w_dur = end_t - start_t
            word_metrics.append((w_L, w_F0, w_dur))
            
        # Z-score 연산 (단어 수가 3개 이상일 때)
        if len(word_metrics) > 2:
            L_vals = np.array([m[0] for m in word_metrics])
            z_L = (L_vals - np.mean(L_vals)) / (np.std(L_vals) + 1e-6)
            
            F0_vals = np.array([m[1] for m in word_metrics])
            z_F0 = (F0_vals - np.mean(F0_vals)) / (np.std(F0_vals) + 1e-6)
            
            dur_vals = np.array([m[2] for m in word_metrics])
            z_dur = (dur_vals - np.mean(dur_vals)) / (np.std(dur_vals) + 1e-6)
            
            stress_scores = z_L + z_F0 + z_dur
            contrast_ratio = stress_scores[target_word_idx] - np.mean(np.delete(stress_scores, target_word_idx))
            stress_accuracy = 1.0 if np.argmax(stress_scores) == target_word_idx else 0.0
        else:
            # Fallback
            stress_scores = [np.mean(m) for m in word_metrics]
            contrast_ratio = stress_scores[target_word_idx] / (np.mean(np.delete(stress_scores, target_word_idx)) + 1e-6)
            stress_accuracy = 1.0 if np.argmax(stress_scores) == target_word_idx else 0.0

        metrics = {"stress_accuracy": float(stress_accuracy), "contrast_ratio": float(contrast_ratio)}
        return self._build_result("stress_contrast", True, ValidityFlag.OK, QualityFlag.OK, metrics)

    def eval_tapping(
        self,
        beat_times: List[float],
        tap_times: List[float],
        read_cue_times: List[float],
        speech_onset_times: List[float],
        tap_tolerance_ms: float = 180.0,
        speech_tolerance_ms: float = 180.0,
    ) -> Dict[str, Any]:
        """#13. 탭핑 (Tapping)

        미리 정해진 리듬(beat_times)에 맞춰 탭(tap_times)과 발화(speech_onset_times)를
        동기화하는 훈련 과제를 평가한다.

        모든 점수는 0.0~1.0 스케일로 반환된다.

        Args:
            beat_times:           메트로놈/cue 리듬의 기준 시각 목록 (초)
            tap_times:            환자가 탭한 시각 목록 (초)
            read_cue_times:       발화 cue 시각 목록 (초) — 언제 읽어야 하는지
            speech_onset_times:   오디오에서 추출된 발화 시작 시각 목록 (초)
            tap_tolerance_ms:     탭 적중 허용 오차 (ms, 기본 180ms)
            speech_tolerance_ms:  발화 적중 허용 오차 (ms, 기본 180ms)

        Returns:
            _build_result() 스키마 결과 dict
            metrics 키:
              tap_sync_error_ms    : 평균 탭-beat 절대오차 (ms)
              tap_hit_rate         : 허용오차 내 탭 비율 (0~1)
              speech_sync_error_ms : 평균 발화-cue 절대오차 (ms)
              speech_hit_rate      : 허용오차 내 발화 비율 (0~1)
              rhythm_stability     : tap interval의 일관성 (0~1)
              overall_score        : 가중 합산 종합점수 (0~1)
            debug 키:
              expected_beat_count, tap_count, speech_onset_count

        TODO(Phase 3): realtime_stream.py 확장 시 tapping live 연동 예정
                      live에서는 WebSocket으로 tap_event를 별도 수신하도록 설계 예정
        """
        debug = {
            "expected_beat_count": len(beat_times),
            "tap_count": len(tap_times),
            "speech_onset_count": len(speech_onset_times),
        }

        # ── 입력 검증 ──────────────────────────────────────────────────
        if len(tap_times) == 0:
            return self._build_result(
                "tapping", False, ValidityFlag.INVALID, QualityFlag.INVALID,
                {"tap_sync_error_ms": 0.0, "tap_hit_rate": 0.0,
                 "speech_sync_error_ms": 0.0, "speech_hit_rate": 0.0,
                 "rhythm_stability": 0.0, "overall_score": 0.0},
                debug=debug
            )

        if len(beat_times) == 0:
            return self._build_result(
                "tapping", False, ValidityFlag.INVALID, QualityFlag.INVALID,
                {"tap_sync_error_ms": 0.0, "tap_hit_rate": 0.0,
                 "speech_sync_error_ms": 0.0, "speech_hit_rate": 0.0,
                 "rhythm_stability": 0.0, "overall_score": 0.0},
                debug=debug
            )

        beat_arr = np.array(beat_times, dtype=float)
        tap_arr  = np.array(tap_times, dtype=float)

        # ── 탭 동기화 오차 & 적중률 ────────────────────────────────────
        tap_errors_ms = []
        for t in tap_arr:
            nearest_beat = beat_arr[np.argmin(np.abs(beat_arr - t))]
            tap_errors_ms.append(abs(t - nearest_beat) * 1000.0)

        tap_errors_ms_arr  = np.array(tap_errors_ms)
        tap_sync_error_ms  = float(np.mean(tap_errors_ms_arr))
        tap_hit_rate       = float(np.mean(tap_errors_ms_arr <= tap_tolerance_ms))

        # ── 발화 동기화 오차 & 적중률 ──────────────────────────────────
        speech_sync_error_ms = 0.0
        speech_hit_rate      = 0.0

        if len(speech_onset_times) == 0 or len(read_cue_times) == 0:
            # 발화가 감지되지 않으면 degraded (탭 평가는 유지)
            q_flag = QualityFlag.DEGRADED
            validity = ValidityFlag.DEGRADED
        else:
            q_flag   = QualityFlag.OK
            validity = ValidityFlag.OK
            cue_arr    = np.array(read_cue_times, dtype=float)
            onset_arr  = np.array(speech_onset_times, dtype=float)

            speech_errors_ms = []
            for cue in cue_arr:
                nearest_onset = onset_arr[np.argmin(np.abs(onset_arr - cue))]
                speech_errors_ms.append(abs(nearest_onset - cue) * 1000.0)

            se_arr               = np.array(speech_errors_ms)
            speech_sync_error_ms = float(np.mean(se_arr))
            speech_hit_rate      = float(np.mean(se_arr <= speech_tolerance_ms))

        # ── 리듬 안정성 (tap interval CV) ──────────────────────────────
        if len(tap_arr) >= 2:
            intervals = np.diff(np.sort(tap_arr))
            mean_iv   = float(np.mean(intervals))
            std_iv    = float(np.std(intervals))
            rhythm_stability = max(0.0, min(1.0, 1.0 - std_iv / (mean_iv + 1e-6)))
        else:
            rhythm_stability = 0.0

        # ── 종합 점수 (0~1) ─────────────────────────────────────────────
        # 오차 기반 보정: 평균 탭 오차가 0에 가까울수록 보너스
        max_expected_err_ms = max(tap_tolerance_ms, speech_tolerance_ms)
        error_bonus = max(
            0.0,
            1.0 - (tap_sync_error_ms + speech_sync_error_ms) / (2.0 * max_expected_err_ms + 1e-6)
        )
        error_bonus = min(error_bonus, 1.0)

        overall_score = (
            tap_hit_rate      * 0.35
            + speech_hit_rate * 0.35
            + rhythm_stability * 0.20
            + error_bonus      * 0.10
        )
        overall_score = max(0.0, min(1.0, overall_score))

        metrics = {
            "tap_sync_error_ms":    tap_sync_error_ms,
            "tap_hit_rate":         tap_hit_rate,
            "speech_sync_error_ms": speech_sync_error_ms,
            "speech_hit_rate":      speech_hit_rate,
            "rhythm_stability":     rhythm_stability,
            "overall_score":        overall_score,
        }

        success = (overall_score >= 0.5)
        return self._build_result("tapping", success, validity, q_flag, metrics, debug=debug)

    def eval_slow_reading(self, audio_duration: float, pause_duration: float, prompt_text: str, target_time_min: Optional[float] = None, target_time_max: Optional[float] = None, asr_tokens: Optional[List[str]] = None) -> Dict[str, Any]:
        """#14. 천천히읽기 (Slow Reading)"""
        prompt_syllables_count = len(prompt_text.replace(" ", ""))
        if audio_duration <= 0:
            return self._build_result("slow_reading", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})
            
        # Fallback: ASR이 망가졌을 수 있으므로 알고 있는 Prompt의 글자 수 활용
        articulation_rate = prompt_syllables_count / (audio_duration - pause_duration) if (audio_duration - pause_duration) > 0 else 0
        pause_ratio = pause_duration / audio_duration
        
        speed_success = True
        if target_time_min is not None:
            speed_success = (audio_duration >= target_time_min)
        if target_time_max is not None and speed_success:
            speed_success = (audio_duration < target_time_max)
        
        metrics = {
            "articulation_rate": float(articulation_rate), 
            "pause_ratio": float(pause_ratio), 
            "audio_duration": float(audio_duration),
            "speed_success": bool(speed_success)
        }
        return self._build_result("slow_reading", speed_success, ValidityFlag.OK, QualityFlag.OK, metrics)

    def eval_loud_reading(self, L_array: np.ndarray, time_axis: np.ndarray, prompt_text: str, normal_reading_loudness: Optional[float] = None, target_gain_db: Optional[float] = None, asr_tokens: Optional[List[str]] = None) -> Dict[str, Any]:
        """#15. 크게읽기 (Loud Reading)"""
        if len(L_array) == 0:
            return self._build_result("loud_reading", False, ValidityFlag.INVALID, QualityFlag.INVALID, {})
            
        mean_loudness = float(np.mean(L_array))
        loudness_stability = 1.0 - (np.std(L_array) / (mean_loudness + 1e-6))
        
        success = True
        gain_db = 0.0
        if normal_reading_loudness is not None:
            gain_db = mean_loudness - normal_reading_loudness
            if target_gain_db is not None:
                success = (gain_db >= target_gain_db)

        metrics = {
            "mean_loudness": mean_loudness, 
            "loudness_stability": max(0.0, float(loudness_stability)),
            "loudness_gain_db": gain_db
        }
        return self._build_result("loud_reading", success, ValidityFlag.OK, QualityFlag.OK, metrics)

    # ==========================================
    # [LIVE] 실시간 UI 피드백용 경량 함수
    # - 0.5초 단기 버퍼 배열을 받아 현재 상태 dict 즉시 반환
    # - _build_result()를 거치지 않아 오버헤드 없음
    # - 기존 최종 평가 함수(eval_*)와 공존하며 절대 대체하지 않음
    # ==========================================

    def eval_voiced_live(self, window_f0: np.ndarray) -> dict:
        """현재 발화 중인지 + 최근 유지 시간 반환 (호흡/발성 공통).
        Returns: {"voiced", "hold_sec", "current_f0"}
        """
        if len(window_f0) == 0:
            return {"voiced": False, "hold_sec": 0.0, "current_f0": 0.0}
        voiced_mask = window_f0 > 0
        # 20ms per frame (parselmouth pitch default time step ≈ 0.02s)
        hold_sec = float(np.sum(voiced_mask)) * 0.02
        current_f0 = float(window_f0[voiced_mask][-1]) if np.any(voiced_mask) else 0.0
        return {"voiced": bool(np.any(voiced_mask)), "hold_sec": hold_sec, "current_f0": current_f0}

    def eval_pitch_live(self, window_f0: np.ndarray, baseline_f0: float) -> dict:
        """최근 0.5초 버퍼 F0 → 현재 피치 상태 즉시 반환.
        Returns: {"current_f0", "voiced", "target_hit", "avg_f0"}
        """
        if len(window_f0) == 0:
            return {"current_f0": 0.0, "voiced": False, "target_hit": False, "avg_f0": 0.0}
        voiced_frames = window_f0[window_f0 > 0]
        if len(voiced_frames) == 0:
            return {"current_f0": 0.0, "voiced": False, "target_hit": False, "avg_f0": 0.0}
        current_f0 = float(voiced_frames[-1])
        avg_f0 = float(np.mean(voiced_frames))
        target_f0 = baseline_f0 * self.config.pitch_target_ratio
        target_hit = abs(current_f0 - target_f0) <= self.config.hz_tolerance
        return {"current_f0": current_f0, "voiced": True, "target_hit": target_hit, "avg_f0": avg_f0}

    def eval_loudness_live(self, window_L: np.ndarray, baseline_L: float, target_gain_db: float) -> dict:
        """최근 0.5초 버퍼 dB → 현재 음량 상태 즉시 반환.
        Returns: {"current_db", "target_db", "target_hit", "avg_db"}
        """
        if len(window_L) == 0:
            return {"current_db": 0.0, "target_db": 0.0, "target_hit": False, "avg_db": 0.0}
        target_db = baseline_L + target_gain_db
        current_db = float(window_L[-1])
        avg_db = float(np.mean(window_L))
        return {
            "current_db": current_db,
            "target_db": target_db,
            "target_hit": current_db >= target_db,
            "avg_db": avg_db
        }

    def eval_breathing_live(self, window_env: np.ndarray, noise_floor: float) -> dict:
        """최근 0.5초 RMS 엔벨로프 → 호흡 감지 여부 즉시 반환.
        Returns: {"exhaling", "current_db", "hold_duration_est"}
        """
        if len(window_env) == 0:
            return {"exhaling": False, "current_db": -60.0, "hold_duration_est": 0.0}
        threshold = noise_floor + 15.0
        exhale_mask = window_env > threshold
        exhaling = bool(np.any(exhale_mask))
        # librosa rms frame step ≈ 512/16000 ≈ 0.032s
        hold_sec = float(np.sum(exhale_mask)) * (512 / 16000)
        return {
            "exhaling": exhaling,
            "current_db": float(window_env[-1]),
            "hold_duration_est": hold_sec
        }


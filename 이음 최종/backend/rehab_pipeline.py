import os
import time
import acoustic_utils as utils
import baseline_estimator
from rehab_evaluator import RehabAudioEvaluator, EvaluatorConfig
from typing import Dict, Any, List

class AudioFeatureCache:
    """오디오 원시 데이터를 파일별 최신 버전에 기반하여 메모리에 캐시합니다."""
    def __init__(self):
        self.cache = {}
        
    def _get_key(self, audio_path: str, feature_type: str) -> str:
        try:
            mtime = os.path.getmtime(audio_path)
            return f"{audio_path}_{mtime}_{feature_type}"
        except OSError:
            return f"{audio_path}_{time.time()}_{feature_type}"
            
    def get(self, audio_path: str, feature_type: str, extractor_func) -> Any:
        key = self._get_key(audio_path, feature_type)
        if key not in self.cache:
            self.cache[key] = extractor_func(audio_path)
        return self.cache[key]

class RehabSessionProcessor:
    """오디오 원시 데이터를 캐싱 분석 모듈로 보내 평가지표를 도출하는 3층 연결 오케스트레이터"""
    def __init__(self, config=None):
        self.config = config or EvaluatorConfig()
        self.evaluator = RehabAudioEvaluator(self.config)
        self.feature_cache = AudioFeatureCache()
        self.baseline = None # Session 단위 공통 세팅
        self._local_baseline_cache = {} # Task-local 단위 캐시
        
    def _get_f0(self, path): return self.feature_cache.get(path, "f0", utils.extract_pitch_track)
    def _get_L(self, path): return self.feature_cache.get(path, "L", utils.extract_intensity_track)
    def _get_onset(self, path): return self.feature_cache.get(path, "onset", utils.extract_onsets)
    def _get_vq(self, path): return self.feature_cache.get(path, "vq", utils.extract_voice_quality_extended)
    def _get_env(self, path): return self.feature_cache.get(path, "env", utils.extract_breath_envelope)

    def set_session_baseline(self, audio_path: str):
        """세션 초기 시작 시 공통 캘리브레이션 모드로 베이스라인 세팅"""
        self.baseline = baseline_estimator.extract_baseline_features(audio_path, mode="session")

    def _ensure_baseline(self, audio_path: str) -> Dict[str, Any]:
        """베이스라인이 없을 시 해당 오디오를 이용해 임시 Task Baseline 추출"""
        if self.baseline is not None:
            return self.baseline
            
        try:
            mtime = os.path.getmtime(audio_path)
            cache_key = f"{audio_path}_{mtime}"
        except OSError:
            cache_key = audio_path
            
        if cache_key not in self._local_baseline_cache:
            self._local_baseline_cache[cache_key] = baseline_estimator.extract_baseline_features(audio_path, mode="task_local")
            
        return self._local_baseline_cache[cache_key]

    # ==========================================
    # 1. 기초 및 호흡/발성 훈련
    # ==========================================
    def process_breathing_proxy(self, audio_path: str) -> Dict[str, Any]:
        """#9/#12. 호흡운동"""
        raw = self._get_env(audio_path)
        base = self._ensure_baseline(audio_path)
        
        dynamic_config = EvaluatorConfig(**{**self.config.__dict__, "min_db_threshold": base["noise_floor"] + 15.0})
        dynamic_evaluator = RehabAudioEvaluator(dynamic_config)
        
        return dynamic_evaluator.eval_breathing_proxy(raw["envelope_array"], raw["time_axis"])

    def process_sustained_phonation(self, audio_path: str, target_duration: float = None) -> Dict[str, Any]:
        """#3. 지속발성"""
        f0_raw = self._get_f0(audio_path)
        L_raw = self._get_L(audio_path)
        
        f0 = f0_raw.get("f0_array", [])
        time_axis = f0_raw.get("time_axis", [])
        voiced_mask = f0 > 0 if len(f0) > 0 else []
        
        return self.evaluator.eval_sustained_phonation(
            voiced_mask, L_raw.get("L_array", []), f0, time_axis, L_raw.get("time_axis", []), target_duration=target_duration
        )

    def process_pitch_glide(self, audio_path: str, direction: str = "up", target_change_percent: float = None, ref_trajectory=None) -> Dict[str, Any]:
        """#4/#5. 음도올리기/내리기"""
        raw = self._get_f0(audio_path)
        return self.evaluator.eval_pitch_glide(raw["f0_array"], raw["time_axis"], direction=direction, target_change_percent=target_change_percent, ref_trajectory=ref_trajectory)

    def process_pitch_control(self, audio_path: str, target_ratio: float = None, hz_tolerance: float = 5.0) -> Dict[str, Any]:
        """#6. 피치조절"""
        raw = self._get_f0(audio_path)
        base = self._ensure_baseline(audio_path)
        t_ratio = target_ratio if target_ratio is not None else self.config.pitch_target_ratio
        return self.evaluator.eval_pitch_control(
            raw["f0_array"], raw["time_axis"], base["baseline_f0"], t_ratio, hz_tolerance=hz_tolerance
        )

    def process_loudness_control(self, audio_path: str, target_gain_db: float = None) -> Dict[str, Any]:
        """#7. 볼륨업"""
        raw = self._get_L(audio_path)
        base = self._ensure_baseline(audio_path)
        gain = target_gain_db if target_gain_db is not None else self.config.loudness_target_gain_db
        return self.evaluator.eval_loudness_control(
            raw["L_array"], raw["time_axis"], base["baseline_loudness"], gain
        )

    def process_glottal_closure(self, audio_path: str) -> Dict[str, Any]:
        """#8. 성문폐쇄"""
        q_raw = self._get_vq(audio_path)
        L_raw = self._get_L(audio_path)
        onsets = self._get_onset(audio_path)
        attack_time = onsets[0] if onsets else 0.0
        
        return self.evaluator.eval_glottal_closure(
            q_raw["hnr"], q_raw["cpp"], q_raw["jitter"], q_raw["shimmer"],
            L_raw.get("L_array", []), attack_time
        )

    # ==========================================
    # 2. 발음 및 말하기 훈련
    # ==========================================
    def process_contrast_drills(self, audio_path: str, logits_matrix, target_idx: int, confusion_idx: int, target_segments: Dict=None) -> Dict[str, Any]:
        """#10. 대조훈련 (REST 후처리 평가)
        
        외부 ASR 로그있이나 정렬 결과를 입력받아 대조 성공 여부를 판단한다.
        
        TODO(Phase 3): alignment_service.py 연동 시 logits/segment 자동 생성 예정
        TODO(Phase 3): realtime_stream.py 확장 시 contrast_drills live 연동 예정
        """
        return self.evaluator.eval_contrast_drills(
            logits_matrix, target_idx, confusion_idx, target_segments=target_segments
        )

    def process_ddk(self, audio_path: str, target_rate: float = None, target_sequence: List[str] = None, predicted_sequence: List[str] = None, alignment_segments: List[Dict] = None) -> Dict[str, Any]:
        """#12. DDK 직접훈련"""
        onsets = self._get_onset(audio_path)
        return self.evaluator.eval_ddk_hybrid(
            onsets, target_rate=target_rate, predicted_sequence=predicted_sequence, target_sequence=target_sequence, alignment_segments=alignment_segments
        )

    def process_stress_contrast(self, audio_path: str, word_timestamps: List[Dict], target_word_idx: int) -> Dict[str, Any]:
        """#11. 대립강세 (REST 후처리 평가)
        
        외부 ASR이 생성한 word_timestamps를 입력받아 강세 대립 성공 여부를 판단한다.
        
        TODO(Phase 3): alignment_service.py 연동 시 word_timestamps 자동 생성 예정
        TODO(Phase 3): realtime_stream.py 확장 시 stress_contrast live 연동 예정
        """
        f0_raw = self._get_f0(audio_path)
        L_raw = self._get_L(audio_path)
        
        L_aligned = self.evaluator._align_array(L_raw.get("L_array", []), L_raw.get("time_axis", []), f0_raw.get("time_axis", []))
        
        return self.evaluator.eval_stress_contrast(
            L_aligned, f0_raw.get("f0_array", []), f0_raw.get("time_axis", []),
            word_timestamps, target_word_idx
        )

    def process_tapping(
        self,
        audio_path: str,
        beat_times: List[float],
        tap_times: List[float],
        read_cue_times: List[float],
        tap_tolerance_ms: float = 180.0,
        speech_tolerance_ms: float = 180.0,
    ) -> Dict[str, Any]:
        """#13. 탭핑 (REST 후처리 평가)

        오디오에서 발화 onset을 추출한 뒤,
        프론트가 전달한 beat/tap/cue 타이밍과 비교하여 리듬 동기화 점수를 반환한다.

        Args:
            audio_path:          평가할 wav 파일 경로
            beat_times:          메트로놈/cue 리듬 기준 시각 목록 (초)
            tap_times:           환자가 탭한 시각 목록 (초)
            read_cue_times:      발화 cue 시각 목록 (초) — 언제 읽어야 하는지
            tap_tolerance_ms:    탭 적중 허용 오차 (ms, 기본 180ms)
            speech_tolerance_ms: 발화 적중 허용 오차 (ms, 기본 180ms)

        Returns:
            _build_result() 스키마 결과 dict

        TODO(Phase 3): realtime_stream.py 확장 시 tapping live 연동 예정
                      live tapping에서는 WebSocket으로 tap_event를 별도 수신하도록 설계 예정
        """
        # 오디오에서 발화 시작 시각 추출 (_get_onset은 feature_cache 활용)
        speech_onset_times = self._get_onset(audio_path)

        return self.evaluator.eval_tapping(
            beat_times=beat_times,
            tap_times=tap_times,
            read_cue_times=read_cue_times,
            speech_onset_times=speech_onset_times,
            tap_tolerance_ms=tap_tolerance_ms,
            speech_tolerance_ms=speech_tolerance_ms,
        )

    def process_slow_reading(self, audio_path: str, prompt_text: str, target_time_min: float = None, target_time_max: float = None, pause_duration: float=0.0) -> Dict[str, Any]:
        """#14. 천천히읽기"""
        import librosa
        y, sr = librosa.load(audio_path, sr=None)
        audio_dur = len(y) / sr        # librosa 0.10+ 호환: filename 파라미터 제거됨
        return self.evaluator.eval_slow_reading(audio_dur, pause_duration, prompt_text, target_time_min=target_time_min, target_time_max=target_time_max)

    def process_loud_reading(self, audio_path: str, prompt_text: str, normal_reading_loudness: float = None, target_gain_db: float = None) -> Dict[str, Any]:
        """#15. 크게읽기"""
        L_raw = self._get_L(audio_path)
        return self.evaluator.eval_loud_reading(
            L_raw.get("L_array", []), L_raw.get("time_axis", []), prompt_text, normal_reading_loudness=normal_reading_loudness, target_gain_db=target_gain_db
        )

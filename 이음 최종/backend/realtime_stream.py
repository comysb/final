# -*- coding: utf-8 -*-
"""
realtime_stream.py
- 목적: 실시간 WebSocket 스트리밍용 5번째 계층
- 역할: 청크 버퍼 관리, 실시간 live feature 추출, 세션 상태 관리
- 원칙:
    * 실시간 UI 피드백과 최종 점수 계산을 분리한다
    * 기존 evaluator(rehab_evaluator.py)는 최종 평가 엔진으로 유지한다
    * rehab_pipeline.py는 세션 종료(finalize) 시에만 호출된다
- 미구현 과제 (현재는 REST만 지원하며, WS는 dummy로 유지):
    * #10 대조훈련, #11 대립강세, #13 탭핑
- TODO(Phase 3): 
    * contrast_drills, stress_contrast, tapping 실시간 live 연동
    * live tapping을 위한 별도 tap event 수신 채널 구현
"""

import collections
import time
import numpy as np
from typing import Optional, Dict, Any

import acoustic_utils as utils
from rehab_evaluator import RehabAudioEvaluator, EvaluatorConfig

# =====================================================================
# 상수
# =====================================================================
CHUNK_SR = 16000            # 16kHz mono (브라우저 AudioWorklet 출력과 동일)
SHORT_BUFFER_SEC  = 0.5     # 실시간 dB/F0 즉시 피드백용  (8,000 샘플)
MEDIUM_BUFFER_SEC = 2.0     # 유지율/단조율 추정용        (32,000 샘플)

# task_type 문자열 → live 피드백 모드 분류
# 과제 번호 기준:
#   breathing(#12), sustained_phonation(#3), glottal_closure(#8) → voiced_live
#   pitch_glide_up(#4), pitch_glide_down(#5)                     → voiced_live
#   pitch_control(#6)                                            → pitch_live
#   loudness_control(#7), loud_reading(#15)                     → loudness_live
#   slow_reading(#14)                                           → voiced_live
#   #10대조훈련, #11대립강세, #13탭핑                            → dummy
_BREATHING_MODE_TASKS = {"breathing"}   # eval_breathing_live() 전용
_VOICED_MODE_TASKS   = {"sustained_phonation", "glottal_closure",
                        "pitch_glide_up", "pitch_glide_down", "slow_reading", "ddk"}
_PITCH_MODE_TASKS    = {"pitch_control"}
_LOUDNESS_MODE_TASKS = {"loudness_control", "loud_reading"}
_DUMMY_TASKS         = {"contrast_drills", "stress_contrast", "tapping"}  # #10, #11, #13


# =====================================================================
# 실시간 과제 세션 객체
# =====================================================================
class RealtimeTaskSession:
    """과제 하나당 하나씩 생성되는 실시간 스트리밍 세션 상태 객체.

    세 종류의 버퍼를 유지한다:
    - ring_short  : 최근 0.5초 PCM — 즉각적인 dB/F0 피드백용 (deque, 자동 제거)
    - ring_medium : 최근 2.0초 PCM — 유지율/단조율 추정용   (deque, 자동 제거)
    - full_buffer : 전체 녹음      — 세션 종료 후 최종 평가용 (list, 무제한)
    """

    def __init__(self, task_type: str, baseline: Dict[str, Any], config: EvaluatorConfig):
        self.task_type = task_type
        self.baseline  = baseline
        self.config    = config
        self.evaluator = RehabAudioEvaluator(config)
        self.created_at = time.time()
        self.cumulative_hold_sec = 0.0  # 누적 발성/호기 시간 추적기
        self.cumulative_success_sec = 0.0  # 누적 성공 시간 추적기

        short_maxlen  = int(SHORT_BUFFER_SEC  * CHUNK_SR)  # 8,000 샘플
        medium_maxlen = int(MEDIUM_BUFFER_SEC * CHUNK_SR)  # 32,000 샘플

        self.ring_short:  collections.deque = collections.deque(maxlen=short_maxlen)
        self.ring_medium: collections.deque = collections.deque(maxlen=medium_maxlen)
        self.full_buffer: list = []

    # ------------------------------------------------------------------
    # 청크 수신
    # ------------------------------------------------------------------
    def push_chunk(self, pcm_chunk: np.ndarray) -> None:
        """100ms PCM Int16 or Float32 청크를 모든 버퍼에 추가한다."""
        # 브라우저에서 Int16 binary로 보낸 경우 float32로 정규화
        if pcm_chunk.dtype == np.int16:
            pcm_chunk = pcm_chunk.astype(np.float32) / 32768.0

        self.ring_short.extend(pcm_chunk.tolist())
        self.ring_medium.extend(pcm_chunk.tolist())
        self.full_buffer.extend(pcm_chunk.tolist())

    # ------------------------------------------------------------------
    # 실시간 피드백 계산
    # ------------------------------------------------------------------
    def get_live_feedback(self) -> dict:
        """SHORT 버퍼(0.5초)로 과제 유형별 실시간 상태를 계산하여 반환한다.

        최소 버퍼 크기(50ms = 800 샘플)에 미달하면 "buffering" 상태를 반환한다.
        미구현 과제(#10, #11, #13)는 {"status": "dummy"}를 반환한다.
        """
        if self.task_type in _DUMMY_TASKS:
            return {"status": "dummy"}

        short_arr = np.array(self.ring_short, dtype=np.float32)
        if len(short_arr) < 800:   # 50ms 미만: 아직 버퍼가 충분하지 않음
            return {"status": "buffering"}

        # 과제 유형별 live 함수 분기
        res = {}
        if self.task_type in _BREATHING_MODE_TASKS:
            # 호흡 과제: RMS 엔벨로프 기반 호기 여부/지속시간 반환
            env_data = utils.extract_breath_envelope_from_array(short_arr, CHUNK_SR)
            res = self.evaluator.eval_breathing_live(
                env_data["envelope_array"],
                self.baseline.get("noise_floor", -60.0)
            )

        elif self.task_type in _VOICED_MODE_TASKS:
            f0_data = utils.extract_pitch_track_from_array(short_arr, CHUNK_SR)
            res = self.evaluator.eval_voiced_live(f0_data["f0_array"])

        elif self.task_type in _PITCH_MODE_TASKS:
            f0_data = utils.extract_pitch_track_from_array(short_arr, CHUNK_SR)
            res = self.evaluator.eval_pitch_live(
                f0_data["f0_array"],
                self.baseline.get("baseline_f0", 150.0)
            )

        elif self.task_type in _LOUDNESS_MODE_TASKS:
            # intensity_track은 target_hit 계산에만 사용 (parselmouth dB SPL 기반)
            # 그러나 UI 표시용 current_db는 표준화 단계에서 rms_spl로 설정됨
            L_data = utils.extract_intensity_track_from_array(short_arr, CHUNK_SR)
            res = self.evaluator.eval_loudness_live(
                L_data["L_array"],
                self.baseline.get("baseline_loudness", -30.0),
                self.config.loudness_target_gain_db
            )
            # parselmouth intensity 기반 current_db 제거 → 표준화 단계에서 rms_spl로 대체
            # (target_hit는 유지)
            res.pop("current_db", None)
            res.pop("avg_db", None)
            res.pop("target_db", None)


        else:
            # 알 수 없는 과제: voiced 여부만 반환
            f0_data = utils.extract_pitch_track_from_array(short_arr, CHUNK_SR)
            res = self.evaluator.eval_voiced_live(f0_data["f0_array"])

        # ─────────────────────────────────────────────────────────────
        # 프론트엔드 필드명 표준화 (frontend _applyLive가 기대하는 키로 통일)
        #
        # 프론트엔드 요구:
        #   data.voiced       → bool   (소리 감지 여부 — wave bar 제어)
        #   data.f0           → float  (Hz — 피치 표시)
        #   data.current_db   → float  (dB SPL/RMS 수준 — 볼륨 표시)
        #   data.target_hit   → bool   (목표 달성 여부)
        # ─────────────────────────────────────────────────────────────

        # ① 실제 RMS dB 계산 (short_arr 기반, 모든 과제 공통)
        rms = float(np.sqrt(np.mean(short_arr ** 2)) + 1e-9)
        rms_db = float(20 * np.log10(rms))   # dBFS (≈ −60 ~ 0)
        spl_offset = 90.0                     # 캘리브레이션 전 기본 오프셋
        rms_spl = rms_db + spl_offset         # ≈ 30~90 dB SPL

        # ② f0: current_f0 → f0 로 통일
        if "current_f0" in res and "f0" not in res:
            res["f0"] = res["current_f0"]

        # ③ voiced 정규화 (누적 시간 이전에 확정)
        if "voiced" not in res:
            if "exhaling" in res:
                res["voiced"] = res["exhaling"]
            else:
                res["voiced"] = rms_spl > 38.0

        # ④ current_db: 공통 RMS 기반 dB
        if "current_db" not in res:
            res["current_db"] = rms_spl

        # ⑤ loudness 과제: target_hit도 rms_spl 기준으로 통일
        if self.task_type in _LOUDNESS_MODE_TASKS:
            TARGET_SPL_THRESHOLD = 70.0
            res["target_hit"] = rms_spl >= TARGET_SPL_THRESHOLD

        # -------------------------------------------------------------
        # 누적 유지 시간 연산 (voiced 확정 후 실행)
        if res.get("voiced", False) or res.get("exhaling", False):
            self.cumulative_hold_sec += 0.1

        if self.task_type in _LOUDNESS_MODE_TASKS and res.get("target_hit", False):
            self.cumulative_success_sec += 0.1

        res["hold_sec"]         = self.cumulative_hold_sec
        res["success_hold_sec"] = self.cumulative_success_sec
        if "hold_duration_est" in res:
            res["hold_duration_est"] = self.cumulative_hold_sec

        return res





    # ------------------------------------------------------------------
    # 세션 종료
    # ------------------------------------------------------------------
    def finalize(self) -> np.ndarray:
        """녹음 종료 시 전체 오디오 float32 배열을 반환한다.
        반환된 배열은 app.py에서 임시 WAV로 저장한 뒤
        기존 rehab_pipeline.process_*()에 전달된다.
        """
        return np.array(self.full_buffer, dtype=np.float32)


# =====================================================================
# 전역 세션 매니저
# =====================================================================
class StreamSessionManager:
    """WebSocket 연결별 RealtimeTaskSession을 관리하는 싱글톤 매니저.

    app.py에서 `stream_manager` 전역 인스턴스를 공유하여 사용한다.
    """

    def __init__(self):
        self._sessions: Dict[str, RealtimeTaskSession] = {}
        self._default_config = EvaluatorConfig()

    def open(self, session_id: str, task_type: str, baseline: Dict[str, Any]) -> RealtimeTaskSession:
        """새 과제 세션을 열고 등록한다."""
        session = RealtimeTaskSession(task_type, baseline, self._default_config)
        self._sessions[session_id] = session
        return session

    def push(self, session_id: str, chunk: np.ndarray) -> None:
        """청크를 해당 세션의 버퍼에 추가한다."""
        if session_id in self._sessions:
            self._sessions[session_id].push_chunk(chunk)

    def feedback(self, session_id: str) -> dict:
        """해당 세션의 실시간 피드백을 계산하여 반환한다."""
        if session_id not in self._sessions:
            return {"error": "session_not_found"}
        return self._sessions[session_id].get_live_feedback()

    def close(self, session_id: str) -> Optional[np.ndarray]:
        """세션을 닫고 전체 오디오 배열을 반환한다. 없으면 None."""
        session = self._sessions.pop(session_id, None)
        if session:
            return session.finalize()
        return None

    @property
    def active_count(self) -> int:
        return len(self._sessions)


# 전역 싱글톤 — app.py에서 `from realtime_stream import stream_manager`로 사용
stream_manager = StreamSessionManager()

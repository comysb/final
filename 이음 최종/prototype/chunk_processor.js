/**
 * chunk_processor.js — AudioWorklet Processor (개선판)
 *
 * 역할: 브라우저 마이크 입력을 100ms 단위로 잘라 16kHz Int16 PCM binary로
 *       변환하여 메인 스레드(WebSocket)로 전달합니다.
 *
 * ✅ 개선사항:
 *   - AudioContext sampleRate가 16kHz가 아닌 경우(44100, 48000 등)
 *     선형보간(linear interpolation) 다운샘플링을 수행합니다.
 *   - 서버는 항상 16kHz Int16 PCM 1600샘플을 수신합니다.
 *   - processor → destination 연결 없음 (스피커 피드백 방지).
 *
 * 서버에서 수신 방법:
 *   np.frombuffer(raw_bytes, dtype=np.int16)  # 항상 1600샘플 @ 16kHz
 */

const TARGET_SR    = 16000;
const CHUNK_MS     = 100;                          // 100ms 단위
const OUT_FRAMES   = (TARGET_SR * CHUNK_MS) / 1000; // 출력: 항상 1600샘플
const INT16_MAX    = 32767;

class ChunkProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        // sampleRate: AudioWorklet 전역값 = AudioContext 실제 샘플레이트
        this._ratio       = sampleRate / TARGET_SR;          // 예: 44100/16000 ≈ 2.756
        this._inputFrames = Math.round(sampleRate * CHUNK_MS / 1000); // 100ms 분량
        this._buffer      = new Float32Array(0);
    }

    /**
     * 선형보간 다운샘플링: float32 배열을 OUT_FRAMES(1600)으로 변환
     * ratio === 1 이면 그대로 반환합니다.
     */
    _downsample(input) {
        if (this._ratio === 1) return input;

        const output = new Float32Array(OUT_FRAMES);
        for (let i = 0; i < OUT_FRAMES; i++) {
            const src  = i * this._ratio;
            const lo   = Math.floor(src);
            const hi   = Math.min(lo + 1, input.length - 1);
            const frac = src - lo;
            output[i]  = input[lo] * (1 - frac) + input[hi] * frac;
        }
        return output;
    }

    process(inputs, outputs, parameters) {
        const inputChannel = inputs[0]?.[0];
        if (!inputChannel || inputChannel.length === 0) return true;

        // 기존 버퍼 + 새 입력 병합
        const merged = new Float32Array(this._buffer.length + inputChannel.length);
        merged.set(this._buffer, 0);
        merged.set(inputChannel, this._buffer.length);
        this._buffer = merged;

        // 입력 측 100ms 단위로 처리
        while (this._buffer.length >= this._inputFrames) {
            const chunk      = this._buffer.slice(0, this._inputFrames);
            this._buffer     = this._buffer.slice(this._inputFrames);

            // → 항상 16kHz 1600샘플로 다운샘플링
            const resampled  = this._downsample(chunk);

            // Float32 [-1.0, 1.0] → Int16 [-32767, 32767]
            const int16      = new Int16Array(OUT_FRAMES);
            for (let i = 0; i < OUT_FRAMES; i++) {
                const clamped = Math.max(-1, Math.min(1, resampled[i]));
                int16[i]      = Math.round(clamped * INT16_MAX);
            }

            // 메인 스레드에 ArrayBuffer 전송 (zero-copy transfer)
            this.port.postMessage(int16.buffer, [int16.buffer]);
        }

        return true;  // 프로세서 유지
    }
}

registerProcessor('chunk-processor', ChunkProcessor);

# -*- coding: utf-8 -*-
"""
acoustic_utils.py
- 합산 파일: 02_forced_alignment.py + 03_extract_features.py (v4)
- 목적: 음성 정렬(MFA/torchaudio) 및 음향 특징 추출(Praat/Wav2Vec2) 핵심 로직 제공
"""

import os
import numpy as np
import parselmouth
import parselmouth.praat
import soundfile as sf
import librosa
from pathlib import Path

# ── 선택적 의존성: torch / torchaudio / transformers ──
# 기본 평가(F0, intensity, RMS, voice quality)는 이 패키지 없이도 동작합니다.
# 음소 정렬(align_word), CTC 디코딩(decode_slplab) 기능만 이 패키지를 필요로 합니다.
try:
    import torch
    import torchaudio
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    print("[WARN] torch/torchaudio/transformers 미설치 — 음소 정렬 기능 비활성")

# =====================================================================
# 상수 및 설정
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
SLPLAB_MODEL = str(BASE_DIR / "models" / "wav2vec2_acoustic")
MFA_DICT_PATH = str(BASE_DIR / "resources" / "korean_mfa.dict")
FRAME_SHIFT = 0.02  # 20ms

DEFAULT_WORDS = [
    "나무", "목도리", "꽃", "김밥", "바지", "사탕", "풍선", "국자",
    "토끼", "코끼리", "해바라기", "연필", "호랑이", "라면", "냉장고",
    "단추", "곰", "가방", "똥", "책상", "자동차", "빨간색", "짹짹",
    "그네", "기차", "접시", "로봇", "싸움", "짜장면", "포크"
]

IPA_TO_SLPLAB = {
    "k":  "G",  "g":  "G",  "ɡ":  "G",
    "p":  "B",  "b":  "B",  "t":  "D",  "d":  "D",
    "k͈":  "GG", "p͈":  "BB", "t͈":  "DD",
    "kʰ": "Kh", "pʰ": "Ph", "tʰ": "Th",
    "k̚":  "G",  "p̚":  "B",  "t̚":  "D",   # Stop symbols unified
    "c":  "G",  "c͈":  "GG",
    "tɕ":  "J",  "dʑ":  "J",  "tɕ͈":  "JJ", "tɕʰ": "CHh",
    "s":   "S",  "sʰ":  "S",  "s͈":   "SS", "ɕ͈":   "SS",
    "m":   "M",  "mʲ":  "M",  "n":   "N",  "ɲ":   "N",  "ŋ":   "NG",
    "l":   "L",  "ɭ":   "L",  "r":   "R",  "ɾ":   "R",  "ɾʲ":  "R",
    "h":   "H",  "ɸʷ":  "H",  "j":   "j",
    "pʲ":  "B",  "tʲ":  "D",
    "ɐ":   "A",  "a":   "A",  "ɐː":  "A",
    "ʌ":   "EO", "ʌː":  "EO",
    "ɨ":   "EU", "ɨː":  "EU",
    "i":   "I",  "iː":  "I",
    "u":   "U",  "uː":  "U",
    "o":   "O",  "oː":  "O",
    "e":   "E",  "eː":  "E",
    "ɛ":   "E",  "ɛː":  "E",
}

DIPHTHONG_MAP = {
    ("j", "A"): "iA", ("j", "E"): "iE", ("j", "EO"): "iEO",
    ("j", "O"): "iO", ("j", "U"): "iU", ("o", "A"): "oA",
    ("o", "E"): "oE", ("u", "EO"): "uEO", ("u", "I"): "uI",
    ("EU", "I"): "euI",
}

CONSONANTS = {
    "k", "g", "p", "b", "t", "d", "m", "n", "ŋ", "l", "r", "s", "h",
    "t͡ɕ", "dʑ", "t͡ɕʰ", "kʰ", "pʰ", "tʰ", "k͈", "p͈", "t͈", "t͡ɕ͈",
    "s͈", "ɕ͈", "ɾ", "ɭ", "c", "ɲ", "k̚", "p̚", "t̚", "ɸʷ",
    "G", "GG", "N", "D", "DD", "L", "M", "B", "BB", "S", "SS", "J", "JJ", "CH", "Kh", "Th", "Ph", "H", "NG", "R", "CHh", "j"
}

VOWELS = {
    "a", "ɐ", "e", "ɛ", "i", "o", "u", "ɨ", "ʌ", "ɯ",
    "ja", "je", "jo", "ju", "jɨ", "jʌ", "wa", "we", "wi", "wɨ",
    "ɯi", "jɛ", "wɛ", "ɰi",
    "A", "EO", "O", "U", "EU", "I", "E", "iA", "iE", "iEO", "iO", "iU", "oA", "oE", "uEO", "uI", "euI",
}

CORNER_VOWELS = {"i", "u", "a", "I", "U", "A"}

MANUAL_CANONICAL_OVERRIDE = {
    "국자": ["G", "U", "G", "J", "A"],
    "해바라기": ["H", "E", "B", "A", "R", "A", "G", "I"],
    "짹짹": ["J", "E", "G", "J", "E", "G"],
}

# =====================================================================
# 유틸리티 함수
# =====================================================================

def load_mfa_dictionary(dict_path: str) -> dict:
    dictionary = {}
    if not os.path.exists(dict_path):
        return dictionary
    with open(dict_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if not parts: continue
            word = parts[0]
            phones = [p for p in parts[1:] if not p.replace('.','',1).isdigit()]
            if phones: dictionary[word] = phones
    return dictionary

def normalize_ipa(ipa: str) -> str:
    if not ipa: return ""
    return ipa.replace("\u0361", "").replace("\u035c", "")

def apply_diphthong_merge(phones: list) -> list:
    result, i = [], 0
    while i < len(phones):
        if i + 1 < len(phones):
            pair = (phones[i], phones[i + 1])
            if pair in DIPHTHONG_MAP:
                result.append(DIPHTHONG_MAP[pair])
                i += 2
                continue
        result.append(phones[i])
        i += 1
    return result

def ipa_to_slplab_seq(ipa_phones: list) -> list:
    mapped = []
    for p in ipa_phones:
        norm_p = normalize_ipa(p)
        m = IPA_TO_SLPLAB.get(norm_p, norm_p)
        if m in (CONSONANTS | VOWELS):
            mapped.append(m)
    return apply_diphthong_merge(mapped)

def g2pk_fallback(word: str) -> list:
    """g2pk -> 자모 -> SlpLab 매핑"""
    try:
        from g2pk import G2p
        pronounced = G2p()(word)
    except:
        pronounced = word

    # 간단 자모 분리 로직 (SlpLab 호환용)
    mapping = {
        "ㄱ":"G","ㄴ":"N","ㄷ":"D","ㄹ":"L","ㅁ":"M","ㅂ":"B","ㅅ":"S","ㅇ":"NG","ㅈ":"J","ㅊ":"CHh",
        "ㅋ":"Kh","ㅌ":"Th","ㅍ":"Ph","ㅎ":"H","ㄲ":"GG","ㄸ":"DD","ㅃ":"BB","ㅆ":"SS","ㅉ":"JJ",
        "ㅏ":"A","ㅐ":"E","ㅑ":"iA","ㅒ":"iE","ㅓ":"EO","ㅔ":"E","ㅕ":"iEO","ㅖ":"iE","ㅗ":"O","ㅘ":"oA",
        "ㅙ":"oE","ㅚ":"O","ㅛ":"iO","ㅜ":"U","ㅝ":"uEO","ㅞ":"uEO","ㅟ":"uI","ㅠ":"iU","ㅡ":"EU","ㅢ":"euI","ㅣ":"I",
    }
    res = []
    for ch in pronounced:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            code -= 0xAC00
            cho = code // (21 * 28)
            jung = (code % (21 * 28)) // 28
            jong = code % 28
            
            CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
            JUNG = ["ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"]
            JONG = ["","ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
            
            if CHO[cho] != "ㅇ": res.append(mapping.get(CHO[cho], ""))
            res.append(mapping.get(JUNG[jung], ""))
            if JONG[jong]: res.append(mapping.get(JONG[jong], ""))
    return [x for x in res if x]

def build_canonical_sequence(word_list: list, mfa_dict: dict) -> tuple:
    can_all, can_cons, can_vows = [], [], []
    for word in word_list:
        if word in MANUAL_CANONICAL_OVERRIDE:
            phones = MANUAL_CANONICAL_OVERRIDE[word]
        elif word in mfa_dict:
            phones = ipa_to_slplab_seq(mfa_dict[word])
        else:
            phones = g2pk_fallback(word)
        can_all += phones
        can_cons += [p for p in phones if p in CONSONANTS]
        can_vows += [p for p in phones if p in VOWELS]
    return can_all, can_cons, can_vows

# =====================================================================
# 정렬 및 특징 추출
# =====================================================================

def align_word(wav_path, word, model, vocab, mfa_dict, device) -> dict:
    if not _TORCH_AVAILABLE:
        return {"alignment": [], "alignment_quality": 0.0}
    try:
        wav, sr = sf.read(wav_path)
        if wav.ndim > 1: wav = wav[:, 0]
        if sr != 16000:
            wav = librosa.resample(wav, orig_sr=sr, target_sr=16000)
            sr = 16000
        wav_t = torch.tensor(wav, dtype=torch.float32).unsqueeze(0).to(device)

        if word in mfa_dict:
            ipa_phones = mfa_dict[word]
            mapped = []
            for p in ipa_phones:
                np_ = normalize_ipa(p)
                m = IPA_TO_SLPLAB.get(np_, np_)
                if m in vocab: mapped.append(m)
            mapped = apply_diphthong_merge(mapped)
            token_ids = [vocab[ph] for ph in mapped]
        else:
            mapped = g2pk_fallback(word)
            token_ids = [vocab[ph] for ph in mapped if ph in vocab]

        if not token_ids: raise ValueError("No valid tokens")

        targets = torch.tensor(token_ids, dtype=torch.int32).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = model(wav_t).logits

        # Forward align logic
        log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
        input_lengths = torch.tensor([log_probs.shape[1]], dtype=torch.int32)
        target_lengths = torch.tensor([len(token_ids)], dtype=torch.int32)
        
        # Blank handling (XLS-R usually has blank at 0)
        alignments, _ = torchaudio.functional.forced_align(
            log_probs.cpu(), targets.cpu(), input_lengths, target_lengths, blank=0
        )
        spans = torchaudio.functional.merge_tokens(alignments[0], torch.zeros_like(alignments[0]))

        res = []
        for i, s in enumerate(spans):
            if i >= len(mapped): break
            res.append({
                "phoneme": mapped[i],
                "start": float(s.start * FRAME_SHIFT),
                "end": float(s.end * FRAME_SHIFT)
            })
        return {"alignment": res, "alignment_quality": 1.0}

    except Exception:
        dur = librosa.get_duration(path=wav_path)
        return {"alignment": [], "alignment_quality": 0.0}

def load_and_trim_clip(wav_path):
    try:
        wav, sr = sf.read(wav_path)
        if wav.ndim > 1: wav = wav[:, 0]
        if sr != 16000: wav = librosa.resample(wav, orig_sr=sr, target_sr=16000)
        trimmed, _ = librosa.effects.trim(wav, top_db=35)
        return trimmed if len(trimmed) >= int(0.1*16000) else wav
    except: return None

def decode_slplab(wav_16k, processor, model, device):
    if not _TORCH_AVAILABLE:
        return []
    inputs = processor(wav_16k, sampling_rate=16000, return_tensors="pt").input_values.to(device)
    with torch.no_grad():
        logits = model(inputs).logits
    p_ids = torch.argmax(logits, dim=-1)[0].tolist()
    
    # Simple CTC decode
    res = []
    prev = None
    v_inv = {v: k for k, v in processor.tokenizer.get_vocab().items()}
    for tid in p_ids:
        if tid != prev and tid != 0:
            lbl = v_inv.get(tid, "")
            lbl = normalize_ipa(lbl)
            lbl = IPA_TO_SLPLAB.get(lbl, lbl)
            if lbl in (CONSONANTS | VOWELS): res.append(lbl)
        prev = tid
    return apply_diphthong_merge(res)

def calc_correct_rate(ref, hyp):
    if not ref: return 0.0
    n, m = len(ref), len(hyp)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(1, n+1): dp[i][0] = -i
    for j in range(1, m+1): dp[0][j] = -j
    for i in range(1, n+1):
        for j in range(1, m+1):
            score = 1 if ref[i-1] == hyp[j-1] else -1
            dp[i][j] = max(dp[i-1][j-1]+score, dp[i-1][j]-1, dp[i][j-1]-1)
    
    i, j, correct = n, m, 0
    while i>0 and j>0:
        score = 1 if ref[i-1] == hyp[j-1] else -1
        if dp[i][j] == dp[i-1][j-1] + score:
            if ref[i-1] == hyp[j-1]: correct += 1
            i-=1; j-=1
        elif dp[i][j] == dp[i-1][j] - 1: i-=1
        else: j-=1
    return (correct / n) * 100.0

def extract_voice_quality(wav_path):
    try:
        sound = parselmouth.Sound(wav_path)
        point_p = parselmouth.praat.call(sound, "To PointProcess (periodic, cc)", 70, 500)
        jitter = parselmouth.praat.call(point_p, "Get jitter (local, absolute)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = parselmouth.praat.call([sound, point_p], "Get shimmer (local, dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        apq = parselmouth.praat.call([sound, point_p], "Get shimmer (apq5)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        return {"jitter": float(jitter), "shimmer": float(shimmer), "apq": float(apq)}
    except: return {"jitter": np.nan, "shimmer": np.nan, "apq": np.nan}

def extract_pitch_features(wav_path):
    try:
        sound = parselmouth.Sound(wav_path)
        pitch = sound.to_pitch()
        f0 = pitch.selected_array["frequency"]
        f0 = f0[f0 > 0]
        return {"mean_f0": np.mean(f0), "median_f0": np.median(f0), "min_f0": np.min(f0), "max_f0": np.max(f0)}
    except: return {"mean_f0": np.nan, "median_f0": np.nan, "min_f0": np.nan, "max_f0": np.nan}

def extract_energy_features(wav_path):
    try:
        sound = parselmouth.Sound(wav_path)
        intensity = sound.to_intensity()
        e = intensity.values.flatten()
        return {"mean_energy": np.mean(e), "median_energy": np.median(e), "std_energy": np.std(e), "min_energy": np.min(e), "max_energy": np.max(e)}
    except: return {"mean_energy": np.nan, "median_energy": np.nan, "std_energy": np.nan, "min_energy": np.nan, "max_energy": np.nan}

def extract_formant_at_midpoint(wav_path, start, end, max_f=5000.0):
    try:
        sound = parselmouth.Sound(wav_path)
        f = sound.to_formant_burg(maximum_formant=max_f)
        mid = (start + end) / 2.0
        return f.get_value_at_time(1, mid), f.get_value_at_time(2, mid)
    except: return None, None

def compute_vsa_metrics(v_pool):
    res = {"vsa_triangle": np.nan, "fcr": np.nan, "vai": np.nan, "f2_ratio": np.nan}
    def get_avg(lst):
        if not lst: return None, None
        return np.mean([x[0] for x in lst]), np.mean([x[1] for x in lst])
    
    f1i, f2i = get_avg(v_pool.get("I", []))
    f1u, f2u = get_avg(v_pool.get("U", []))
    f1a, f2a = get_avg(v_pool.get("A", []))
    
    if all(v is not None for v in [f1i, f2i, f1u, f2u, f1a, f2a]):
        vsa = 0.5 * abs(f2i*(f1a-f1u) + f2a*(f1u-f1i) + f2u*(f1i-f1a))
        fcr = (f2u + f2a + f1i + f1u) / (f2i + f1a)
        vai = 1 / fcr
        f2r = f2i / f2u
        res.update({"vsa_triangle": vsa, "fcr": fcr, "vai": vai, "f2_ratio": f2r})
    return res

# =====================================================================
# 재활 훈련 파이프라인 전용 시계열(Track)/배열 추출기
# =====================================================================

def extract_pitch_track(wav_path):
    """시계열 피치 배열 및 시간축 반환"""
    try:
        sound = parselmouth.Sound(wav_path)
        pitch = sound.to_pitch()
        f0 = pitch.selected_array["frequency"]
        time_axis = pitch.xs()
        return {"f0_array": f0, "time_axis": time_axis}
    except Exception as e:
        return {"f0_array": np.array([]), "time_axis": np.array([])}

def extract_intensity_track(wav_path):
    """시계열 음량 배열 및 시간축 반환"""
    try:
        sound = parselmouth.Sound(wav_path)
        intensity = sound.to_intensity()
        L = intensity.values.flatten()
        time_axis = intensity.xs()
        return {"L_array": L, "time_axis": time_axis}
    except Exception as e:
        return {"L_array": np.array([]), "time_axis": np.array([])}

def extract_voice_quality_extended(wav_path):
    """HNR, CPP를 포함한 확장 질적 피처 추출기"""
    res = {"hnr": 0.0, "cpp": None, "jitter": 0.0, "shimmer": 0.0}
    try:
        sound = parselmouth.Sound(wav_path)
        harmonicity = sound.to_harmonicity_cc()
        hnr = np.nanmean(harmonicity.values[harmonicity.values != -200]) # Praat uses -200 as silence
        res["hnr"] = float(hnr) if not np.isnan(hnr) else 0.0
        
        # CPP (Cepstral Peak Prominence) 추출
        # PowerCepstrogram 생성: pitch floor=60, default param
        try:
            pitch = sound.to_pitch()
            cepstrogram = parselmouth.praat.call(sound, "To PowerCepstrogram", 60.0, 0.002, 5000.0, 50.0)
            cpp = parselmouth.praat.call(cepstrogram, "Get CPPS", True, 0.01, 0.001, 60.0, 330.0, 0.05, "Parabolic", 0.001, 0.05, "Straight", "Robust")
            res["cpp"] = float(cpp) if not np.isnan(cpp) else None
        except:
            res["cpp"] = None

        # Jitter/Shimmer
        pulses = parselmouth.praat.call([sound, pitch], "To PointProcess (cc)")
        res["jitter"] = parselmouth.praat.call(pulses, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3)
        res["shimmer"] = parselmouth.praat.call([sound, pulses], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    except:
        pass
    return res

def extract_onsets(wav_path):
    """onset detect를 이용하여 타격점(sec)들 반환"""
    try:
        y, sr = librosa.load(wav_path, sr=16000)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        return onset_times.tolist()
    except:
        return []

def extract_breath_envelope(wav_path):
    """RMS Energy envelope (Proxy for breathing)"""
    try:
        y, sr = librosa.load(wav_path, sr=16000)
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        # Convert RMS to absolute dBFS using ref=1.0 (where 1.0 is full scale max)
        env_db = librosa.amplitude_to_db(rms, ref=1.0)
        return {"envelope_array": env_db, "time_axis": times}
    except:
        return {"envelope_array": np.array([]), "time_axis": np.array([])}


# =====================================================================
# 실시간 스트리밍 전용 — 배열 입력 버전 (반환 스키마 동일)
# 기존 파일 기반 함수와 동일한 dict를 반환하되, wav 파일 I/O 없이
# numpy 배열을 직접 입력받아 처리합니다.
# =====================================================================

def extract_pitch_track_from_array(audio_array: np.ndarray, sr: int = 16000) -> dict:
    """실시간 청크용: numpy 배열 → 피치 트랙.
    반환 스키마: extract_pitch_track()과 동일 {"f0_array", "time_axis"}
    """
    try:
        # parselmouth.Sound는 (samples, sr) 형식의 배열을 직접 지원
        sound = parselmouth.Sound(audio_array.astype(np.float64), sampling_frequency=float(sr))
        pitch = sound.to_pitch()
        f0 = pitch.selected_array["frequency"]
        time_axis = pitch.xs()
        return {"f0_array": f0, "time_axis": time_axis}
    except Exception:
        return {"f0_array": np.array([]), "time_axis": np.array([])}


def extract_intensity_track_from_array(audio_array: np.ndarray, sr: int = 16000) -> dict:
    """실시간 청크용: numpy 배열 → 음량 트랙 (dB SPL).
    반환 스키마: extract_intensity_track()과 동일 {"L_array", "time_axis"}
    """
    try:
        sound = parselmouth.Sound(audio_array.astype(np.float64), sampling_frequency=float(sr))
        intensity = sound.to_intensity()
        L = intensity.values.flatten()
        time_axis = intensity.xs()
        return {"L_array": L, "time_axis": time_axis}
    except Exception:
        return {"L_array": np.array([]), "time_axis": np.array([])}


def extract_breath_envelope_from_array(audio_array: np.ndarray, sr: int = 16000) -> dict:
    """실시간 청크용: numpy 배열 → RMS 에너지 엔벨로프 (dBFS).
    반환 스키마: extract_breath_envelope()과 동일 {"envelope_array", "time_axis"}
    """
    try:
        rms = librosa.feature.rms(y=audio_array)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        env_db = librosa.amplitude_to_db(rms, ref=1.0)
        return {"envelope_array": env_db, "time_axis": times}
    except Exception:
        return {"envelope_array": np.array([]), "time_axis": np.array([])}

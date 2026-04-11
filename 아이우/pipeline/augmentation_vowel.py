import os
import sys
import numpy as np
import pandas as pd
import librosa
import soundfile as sf
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *
from pipeline.data_loader import load_mapping

PRAAT_FEATURES_CSV = os.path.join(RESULTS_DIR, "features_cv_smote.csv")
AUG_AUDIO_DIR = os.path.join(BASE_DIR, "augmented_audio")
AUG_MAPPING_CSV = os.path.join(AUG_AUDIO_DIR, "augmented_mapping.csv")

def augment_pitch(y, sr, n_steps):
    return librosa.effects.pitch_shift(y=y, sr=sr, n_steps=n_steps)

def augment_gain(y, db_change):
    factor = 10 ** (db_change / 20.0)
    return y * factor

def augment_noise(y, snr_db=25):
    signal_power = np.mean(y ** 2)
    noise_power = signal_power / (10 ** (snr_db / 10.0))
    noise = np.random.normal(0, np.sqrt(noise_power), len(y))
    return y + noise

def augment_time_shift(y, sr, max_shift_ms=200):
    shift_amount = int(np.random.uniform(100, max_shift_ms) * sr / 1000.0)
    direction = np.random.choice(["left", "right"])
    if direction == "left":
        return np.roll(y, -shift_amount)
    else:
        return np.roll(y, shift_amount)

def augment_time_masking(y, sr, max_mask_ms=200):
    mask_len = int(np.random.uniform(50, max_mask_ms) * sr / 1000.0)
    if mask_len >= len(y):
        mask_len = len(y) // 2
    mask_start = np.random.randint(0, len(y) - mask_len)
    
    y_masked = y.copy()
    y_masked[mask_start:mask_start+mask_len] = 0
    return y_masked

def save_wav(y, sr, path):
    # normalize slightly to prevent clipping if gain caused it
    max_val = np.max(np.abs(y))
    if max_val > 1.0:
        y = y / max_val
    sf.write(path, y, sr)

def main():
    if not os.path.exists(AUG_AUDIO_DIR):
        os.makedirs(AUG_AUDIO_DIR)
        
    print("=== 모음 특화 물리적 파형 증강망 (Severe Class) ===")
    
    df_praat = pd.read_csv(PRAAT_FEATURES_CSV, encoding="utf-8-sig")
    df_map = load_mapping(verbose=False)
    df_map_indexed = df_map.set_index("UID")
    
    # 중증(Severe) 케이스만 필터링 (장애정도 == 2)
    severe_uids = df_praat[df_praat['장애정도'] == 2]['UID'].values
    print(f"중증 세션 수: {len(severe_uids)}개")
    
    aug_records = []
    
    for uid in tqdm(severe_uids, desc="중증 환자 파형 증강"):
        row = df_map_indexed.loc[uid]
        speaker_id = df_praat[df_praat['UID'] == uid]['speaker_id'].values[0]
        label = 2
        
        # Paths
        paths = {
            "아": row["path_아"],
            "이": row["path_이"],
            "우": row["path_우"]
        }
        
        # Vowels to process
        vowels_conf = {
            "아": ["p_up", "p_dn", "g_up", "g_dn", "noise", "t_mask", "t_mask2"],
            "이": ["p_up", "p_dn", "g_up", "g_dn", "noise", "t_shift", "t_shift2", "t_mask", "t_mask2"],
            "우": ["p_up", "p_dn", "g_up", "g_dn", "noise", "t_mask", "t_mask2"]
        }
        
        # We will generate matched sets of [아, 이, 우] if possible, to keep the mapping structure.
        # But wait, each vowel has missing files sometimes. 
        # By the user's manual count, /아/ has 7, /이/ has 5, /우/ has 6.
        # It's better to just generate 7 variants per UID.
        variants = ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]
        
        for v_idx, variant in enumerate(variants):
            new_uid = f"{uid}_aug_{variant}"
            
            new_paths = {"아": "", "이": "", "우": ""}
            has_any = False
            
            for v, p in paths.items():
                if pd.isna(p) or not os.path.exists(str(p)):
                    continue
                    
                y, sr = librosa.load(p, sr=16000)
                
                # Apply specific augmentation based on variant and vowel constraints
                try:
                    if variant == "v1": # Pitch +2st
                        y_aug = augment_pitch(y, sr, 2)
                    elif variant == "v2": # Pitch -2st
                        y_aug = augment_pitch(y, sr, -2)
                    elif variant == "v3": # Gain -8dB
                        y_aug = augment_gain(y, -8)
                    elif variant == "v4": # Gain +4dB
                        y_aug = augment_gain(y, 4)
                    elif variant == "v5": # Noise 25dB
                        y_aug = augment_noise(y, 25)
                    elif variant == "v6": # Masking or Shift
                        if v == "이":
                            y_aug = augment_time_shift(y, sr, 200)
                        else:
                            y_aug = augment_time_masking(y, sr, 200)
                    elif variant == "v7": # Additional Masking
                        y_aug = augment_time_masking(y, sr, 300)
                except Exception as e:
                    print(f"Error augmenting {p}: {e}")
                    y_aug = y.copy()
                    
                out_path = os.path.join(AUG_AUDIO_DIR, f"{new_uid}_{v}.wav")
                save_wav(y_aug, sr, out_path)
                new_paths[v] = out_path
                has_any = True
                
            if has_any:
                aug_records.append({
                    "UID": new_uid,
                    "speaker_id": speaker_id,  # 중요: GroupKFold Leakage 방지용 원본 화자 ID
                    "장애정도": label,
                    "path_아": new_paths["아"],
                    "path_이": new_paths["이"],
                    "path_우": new_paths["우"],
                    "augmented": 1,
                    "aug_type": variant
                })
                
    df_aug = pd.DataFrame(aug_records)
    df_aug.to_csv(AUG_MAPPING_CSV, index=False, encoding="utf-8-sig")
    print(f"\n파형 증강 완료! 총 {len(df_aug)}개의 합성 세션 생성됨.")
    print(f"매핑 정보 저장: {AUG_MAPPING_CSV}")

if __name__ == "__main__":
    main()

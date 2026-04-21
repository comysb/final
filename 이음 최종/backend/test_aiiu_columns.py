import sys
import os
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\아이우")

from pipeline.inference_engine import DysarthriaInferenceEngine
import soundfile as sf

e = DysarthriaInferenceEngine()

print("=== feat_cols (112개) ===")
for i, col in enumerate(e.feat_cols):
    print(f"  [{i:3d}] {col!r}")

# Also test extract_features with real wav
print("\n=== extract_features 테스트 ===")
sr = 16000
duration = 3.0
t = np.linspace(0, duration, int(sr * duration))
y = 0.3 * np.sin(2 * np.pi * 220 * t)
for name in ["test_a.wav", "test_i.wav", "test_u.wav"]:
    sf.write(name, y, sr)

result = e.extract_features("test_a.wav", "test_i.wav", "test_u.wav")
print("타입:", type(result))
print("shape:", result.shape if isinstance(result, np.ndarray) else "N/A")
print("첫 15개 값:", result[0, :15] if isinstance(result, np.ndarray) else result)

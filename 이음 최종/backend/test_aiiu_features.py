import sys
import os
import traceback

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\이음복사본1\backend")
os.chdir(r"D:\이음복사본1\backend")

# Test AiiuEngine.extract_features with a dummy wav
print("=== AiiuEngine extract_features 테스트 ===")
try:
    from main import AiiuEngine
    import soundfile as sf
    import numpy as np

    engine = AiiuEngine()
    
    # Create a simple test wav
    sr = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration))
    y = 0.3 * np.sin(2 * np.pi * 220 * t)
    
    for name in ["test_a.wav", "test_i.wav", "test_u.wav"]:
        sf.write(name, y, sr)
    
    feats = engine.engine.extract_features("test_a.wav", "test_i.wav", "test_u.wav")
    print("extract_features 타입:", type(feats))
    if isinstance(feats, dict):
        print("반환된 피처 키 목록:")
        for k, v in feats.items():
            print(f"  {k!r}: {v}")
    else:
        print("결과:", feats)
        
except Exception as e:
    traceback.print_exc()
    print("FAILED:", e)

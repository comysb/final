import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# 1. Check noise/dB check feature
print("=== 1. 소음 체크 (30dB) 기능 확인 ===")
noise_keywords = ['30', 'dB', 'noiseChunks', 'sevCalibrat', 'calibrat', 'sevCalib', 'ambient']
for kw in noise_keywords:
    in_b = kw in backup
    in_c = kw in current
    status = 'OK' if in_b == in_c else 'MISSING' if in_b and not in_c else 'DIFFERENT'
    print(f"  {kw}: backup={in_b}, current={in_c} [{status}]")

# Show the noise check function from backup
print("\n--- 소음 체크 로직 from backup ---")
# Check for noise-related code
for kw in ['noiseChunks', 'sevCalibrat', '30']:
    idx = backup.find(kw)
    if idx != -1:
        start = max(0, idx - 100)
        print(f"\n[{kw}]:", backup[start:idx+200].encode('cp949', 'replace').decode('cp949'))

# 2. Check daily training recommendation feature
print("\n\n=== 2. 오늘의 훈련 추천 기능 확인 ===")
training_keywords = ['buildAndGotoTodayTraining', 'renderTodayTraining', 'today-training', 'screen-today-training', 'TASK_POOL', 'todayPlan']
for kw in training_keywords:
    in_b = kw in backup
    in_c = kw in current
    status = 'OK' if in_b == in_c else 'MISSING' if in_b and not in_c else 'EXTRA'
    print(f"  {kw}: backup={in_b}, current={in_c} [{status}]")

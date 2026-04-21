import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

checks = {
    'startSevCalibration': '소음 캘리브레이션 시작 함수',
    'noiseChunks': '소음 녹음 변수',
    'buildAndGotoTodayTraining': '오늘의 훈련 추천 함수',
    'renderTodayTraining': '오늘의 훈련 렌더링 함수',
    'screen-today-training': '오늘의 훈련 화면 DOM',
}

for key, desc in checks.items():
    in_b = key in backup
    in_c = key in current
    if in_b and not in_c:
        print(f"MISSING: {key} ({desc})")
    elif in_b and in_c:
        print(f"EXISTS: {key} ({desc})")
    elif not in_b:
        print(f"NOT IN BACKUP: {key} ({desc})")

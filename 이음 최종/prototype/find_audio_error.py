import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Find where "오디오 인식" or "인식에 실패" message appears
for kw in ['인식에 실패', '인식이 실패', '오디오 인식', 'audio fail', 'getUserMedia']:
    idx = text.find(kw)
    if idx != -1:
        start = max(0, idx - 200)
        end = min(len(text), idx + 300)
        print(f"=== [{kw}] found ===")
        print(text[start:end].encode('cp949', 'replace').decode('cp949'))
        print()

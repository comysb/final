import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

idx = text.find('triggerWarning')
if idx != -1:
    start = max(0, idx - 100)
    end = min(len(text), idx + 2000)
    print("Found triggerWarning:")
    print(text[start:end].encode('cp949', 'replace').decode('cp949'))

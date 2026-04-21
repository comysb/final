import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Find all code around sev-analyzing-view (the spinner screen)
idx = text.find('sev-analyzing-view')
if idx != -1:
    start = max(0, idx - 500)
    end = min(len(text), idx + 2000)
    print(text[start:end].encode('cp949', 'replace').decode('cp949'))

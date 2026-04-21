import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Find the severity analysis / prediction submit flow
for keyword in ['submitSev', 'analyzeSev', 'predictSev', 'goto.*sev', 'severity.*result', 'screen-sev', 'analyzing', 'analysisResult']:
    matches = list(re.finditer(keyword, text, re.IGNORECASE))
    if matches:
        m = matches[0]
        start = max(0, m.start() - 30)
        end = min(len(text), m.end() + 100)
        print(f"=== {keyword} ===")
        print(text[start:end].encode('cp949', 'replace').decode('cp949'))

import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Find sevNextStep function and the full analysis function
idx = text.find('function sevNextStep')
if idx != -1:
    print(text[idx:idx+3000].encode('cp949', 'replace').decode('cp949'))
else:
    print("sevNextStep not found. Looking for sevDoAnalyze or similar...")
    for kw in ['sevAnalyz', 'doAnalyz', 'analyzeAll', 'showSevResult', 'sevSubmit', 'api/predict']:
        idx = text.find(kw)
        if idx != -1:
            print(f"=== {kw} at {idx} ===")
            print(text[idx:idx+500].encode('cp949', 'replace').decode('cp949'))

import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Let's find "27개" exactly in the text!
matches = re.finditer(r'27', text)
for m in matches:
    start = max(0, m.start() - 30)
    end = min(len(text), m.end() + 30)
    print("MATCH 27:", text[start:end].encode('cp949', 'replace').decode('cp949'))

# Also, let's find the array of words
import json
arrays = re.findall(r'\[\s*(?:[\'\"].*?[\'\"]\s*,\s*)*[\'\"].*?[\'\"]\s*\]', text, flags=re.DOTALL)
for arr in arrays:
    if len(arr) > 100:
        print("ARRAY snippet:", arr[:150].encode('cp949', 'replace').decode('cp949'))

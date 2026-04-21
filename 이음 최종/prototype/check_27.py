import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

count = 0
for m in re.finditer(r'27', text):
    start = max(0, m.start() - 20)
    end = min(len(text), m.end() + 20)
    print("Match found:", text[start:end].encode('cp949', 'replace').decode('cp949'))
    count += 1
print(f"Total 27s found: {count}")

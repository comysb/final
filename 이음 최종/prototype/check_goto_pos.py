import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

for m in re.finditer(r'function goto\(', text):
    start = max(0, m.start() - 50)
    print("--- FOUND GOTO ---")
    print(text[start:m.start()+500].encode('cp949', 'replace').decode('cp949'))

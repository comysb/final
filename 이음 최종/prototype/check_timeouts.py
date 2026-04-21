import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

for m in re.finditer(r'setTimeout\(\(\)\s*=>\s*\{?\s*goto\(.*?\}?,?\s*\d+\)', text):
    start = max(0, m.start() - 50)
    print("--- FOUND GOTO SETTIMEOUT ---")
    print(text[start:m.end()+50])

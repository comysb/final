import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

for i, m in enumerate(re.finditer(r'window\.addEventListener\([\'\"]hashchange[\'\"].*?\}\);', text, flags=re.DOTALL)):
    print(f"--- MATCH {i} ---")
    print(m.group(0)[:300].encode('cp949', 'replace').decode('cp949'))

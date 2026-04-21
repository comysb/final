import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

count = len(re.findall(r'function goto\(', text))
print("GOTO count:", count)

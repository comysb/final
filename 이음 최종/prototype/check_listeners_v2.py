import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

count_hash = len(re.findall(r'hashchange', text))
count_dom = len(re.findall(r'DOMContentLoaded', text))

print(f"hashchange count: {count_hash}")
print(f"DOMContentLoaded count: {count_dom}")

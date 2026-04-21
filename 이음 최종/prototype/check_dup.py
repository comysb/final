import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

listeners = []
for m in re.finditer(r'window\.addEventListener\([\'\"]hashchange[\'\"].*?\}\);', text, flags=re.DOTALL):
    listeners.append(m.group(0))

for i, l in enumerate(listeners):
    print(f"\n--- LISTENER {i} ---")
    print(l[:300])
    
print("\n--- DOMContentLoaded LISTENER ---")
for m in re.finditer(r'window\.addEventListener\([\'\"]DOMContentLoaded[\'\"].*?\}\);', text, flags=re.DOTALL):
    print(m.group(0)[:300])


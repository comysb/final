import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Search for the video tag
print("=== Video tags ===")
for m in re.finditer(r'<video[^>]*>', text):
    print(m.group(0))

# Search for video assignment
print("\n=== Video source assignments ===")
for m in re.finditer(r'\.src\s*=\s*', text):
    start = max(0, m.start()-50)
    end = min(len(text), m.end()+150)
    print(text[start:end])

# Search for openTodayExSingle which might set the video
idx = text.find('function openTodayExSingle')
if idx != -1:
    print("\n=== function openTodayExSingle ===")
    print(text[idx:idx+800].encode('cp949', 'replace').decode('cp949'))

import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Find VIDEO_MAP
idx = text.find('VIDEO_MAP')
if idx != -1:
    print("Found VIDEO_MAP at index:", idx)
    # Extract around it
    # Find the = sign and then the object
    start = max(0, idx - 10)
    print(text[start:start+1000].encode('cp949', 'replace').decode('cp949'))
else:
    print("VIDEO_MAP NOT FOUND in current file!")

# Also check backup
with codecs.open(r'D:\이음\이음복사본\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    backup = f.read()

idx2 = backup.find('VIDEO_MAP')
if idx2 != -1:
    print("\n=== VIDEO_MAP in BACKUP ===")
    print(backup[idx2:idx2+1000].encode('cp949', 'replace').decode('cp949'))
else:
    print("VIDEO_MAP NOT in backup either!")

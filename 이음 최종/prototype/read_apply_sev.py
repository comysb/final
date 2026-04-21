import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()

with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Extract applySevResultUI from backup to understand the correct UI logic
idx = backup.find('function applySevResultUI')
brace_count = 0
idx_end = -1
for i in range(idx, len(backup)):
    if backup[i] == '{':
        brace_count += 1
    elif backup[i] == '}':
        brace_count -= 1
        if brace_count == 0:
            idx_end = i + 1
            break

if idx_end != -1:
    fn_code = backup[idx:idx_end]
    print("applySevResultUI from backup:")
    print(fn_code.encode('cp949', 'replace').decode('cp949'))

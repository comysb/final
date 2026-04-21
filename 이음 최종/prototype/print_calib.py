import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Print the backup startSevCalibration to see the 30dB threshold
def extract_fn(text, name):
    idx = text.find(f'function {name}')
    if idx == -1:
        return None
    brace_count = 0
    started = False
    for i in range(idx, len(text)):
        if text[i] == '{':
            started = True
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if started and brace_count == 0:
                return text[idx:i+1]
    return None

fn = extract_fn(backup, 'startSevCalibration')
print("Backup startSevCalibration:")
print(fn.encode('cp949', 'replace').decode('cp949'))

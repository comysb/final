import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Extract startSevCalibration from backup (full function with noiseChunks logic)
def extract_fn(text, name):
    idx = text.find(f'function {name}')
    if idx == -1:
        return None, -1
    brace_count = 0
    started = False
    for i in range(idx, len(text)):
        if text[i] == '{':
            started = True
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if started and brace_count == 0:
                return text[idx:i+1], i+1
    return None, -1

backup_calib_fn, _ = extract_fn(backup, 'startSevCalibration')
if backup_calib_fn:
    print("Found startSevCalibration in backup")
    print("Length:", len(backup_calib_fn))
    print("Has noiseChunks:", 'noiseChunks' in backup_calib_fn)
    print("Has 30dB check:", '30' in backup_calib_fn and 'dB' in backup_calib_fn)

# Also check what's in current startSevCalibration
current_calib_fn, _ = extract_fn(current, 'startSevCalibration')
if current_calib_fn:
    print("\nCurrent startSevCalibration length:", len(current_calib_fn))
    print("Has noiseChunks:", 'noiseChunks' in current_calib_fn)

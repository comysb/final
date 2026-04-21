import codecs
import re

current_path = r'D:\이음\prototype\therapy_ui_v4.html'
backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()

# Extract the full startSevCalibration from backup
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

backup_calib = extract_fn(backup, 'startSevCalibration')

# The backup function uses await but is not declared async - fix that
# The function in backup is NOT declared as async but uses await inside it
# Need to make it async
backup_calib_fixed = backup_calib.replace('function startSevCalibration()', 'async function startSevCalibration()')

with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Replace current startSevCalibration with backup's full version
current_calib = extract_fn(current, 'startSevCalibration')
if current_calib:
    current = current.replace(current_calib, backup_calib_fixed)
    print("Replaced startSevCalibration with backup version (with noise check)!")
else:
    # Try async version
    current_calib = extract_fn(current, 'startSevCalibration')
    print("Not found in current")

with codecs.open(current_path, 'w', 'utf-8') as f:
    f.write(current)

print("Done!")

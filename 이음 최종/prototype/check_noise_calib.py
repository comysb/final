import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Extract the full noise calibration function from backup  
# Find the function containing noiseChunks / sevCalibrated
idx = backup.find('noiseChunks')
start = max(0, idx - 500)
end = min(len(backup), idx + 2000)
print("=== Full noise calibration block from backup ===")
print(backup[start:end].encode('cp949', 'replace').decode('cp949'))

print("\n\n=== What current has for sevCalib ===")
idx2 = current.find('sevCalibrated')
if idx2 != -1:
    start2 = max(0, idx2 - 100)
    end2 = min(len(current), idx2 + 500)
    print(current[start2:end2].encode('cp949', 'replace').decode('cp949'))

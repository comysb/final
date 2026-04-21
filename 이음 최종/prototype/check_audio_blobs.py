import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Check how audioBlobs are saved during severity recording in backup
# Look for where blobs are assigned per task
matches = []
for m in re.finditer(r'audioBlobs', backup):
    start = max(0, m.start() - 80)
    end = min(len(backup), m.end() + 80)
    context = backup[start:end].encode('cp949', 'replace').decode('cp949')
    matches.append(context)

print("=== audioBlobs usage in backup ===")
for i, ctx in enumerate(matches):
    print(f"--- {i} ---")
    print(ctx)

import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Extract ALL function names from backup
backup_fns = set(re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', backup))
current_fns = set(re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', current))

missing = backup_fns - current_fns
extra = current_fns - backup_fns

print("Functions in BACKUP but MISSING from current:")
for fn in sorted(missing):
    print(" -", fn)

print("\nFunctions in current but NOT in backup (new additions):")
for fn in sorted(extra):
    print(" +", fn)

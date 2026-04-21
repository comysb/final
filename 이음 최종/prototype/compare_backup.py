import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

print('BACKUP size:', len(backup))
print('CURRENT size:', len(current))

# Check word array in backup
m = re.search(r'const SEV_WORDS_RAW\s*=\s*\[.*?\];', backup, flags=re.DOTALL)
if m:
    words = re.findall(r"['\"]([^'\"]+)['\"]", m.group(0))
    print('Backup SEV_WORDS_RAW count:', len(words))
    print('Words:', words)

# Check word array in current
m2 = re.search(r'const SEV_WORDS_RAW\s*=\s*\[.*?\];', current, flags=re.DOTALL)
if m2:
    words2 = re.findall(r"['\"]([^'\"]+)['\"]", m2.group(0))
    print('\nCurrent SEV_WORDS_RAW count:', len(words2))

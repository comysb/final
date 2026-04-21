import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'
current_path = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()

with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Compare key data variables
key_vars = ['SEV_DDK', 'SEV_TASKS', 'LEVELS', 'DATA_TASKS', 'DOMAIN_TASKS', 'EXER_DB']
for var in key_vars:
    in_backup = var in backup
    in_current = var in current
    status = 'OK' if in_backup == in_current else 'MISSING' if in_backup and not in_current else 'EXTRA'
    print(f"{var}: backup={in_backup}, current={in_current} [{status}]")

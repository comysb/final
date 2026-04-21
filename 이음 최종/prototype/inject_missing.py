import codecs
import re

current_path = r'D:\이음\prototype\therapy_ui_v4.html'
backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'

with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()

# 1. Load the missing functions JS
with codecs.open(r'D:\이음\prototype\missing_functions.js', 'r', 'utf-8') as f:
    missing_fns_code = f.read()

# 2. Inject missing functions before </script> (last one)
# Find the last </script> and insert before it
last_script_end = current.rfind('</script>')
if last_script_end != -1:
    current = current[:last_script_end] + "\n\n" + missing_fns_code + "\n\n" + current[last_script_end:]
    print("Injected missing functions into therapy_ui_v4.html")
else:
    print("Could not find </script> tag!")

# 3. Fix SEV_WORDS_RAW - copy from backup
backup_words_m = re.search(r'const SEV_WORDS_RAW\s*=\s*\[.*?\];', backup, flags=re.DOTALL)
current_words_m = re.search(r'const SEV_WORDS_RAW\s*=\s*\[.*?\];', current, flags=re.DOTALL)
if backup_words_m and current_words_m:
    current = current[:current_words_m.start()] + backup_words_m.group(0) + current[current_words_m.end():]
    print("Replaced SEV_WORDS_RAW with backup version")

# 4. Fix applySevResultUI - replace my bad renderSevResult with backup's applySevResultUI
# The current doSevAnalysis calls renderSevResult - let it also call applySevResultUI
current = current.replace('renderSevResult(results);', 'renderSevResult(results);\n  applySevResultUI(results);')

# 5. Copy the full showSevResult block from backup if it exists there
backup_sev_result_ui_idx = backup.find('function applySevResultUI')
if backup_sev_result_ui_idx != -1:
    print("applySevResultUI found in backup - already extracted")

with codecs.open(current_path, 'w', 'utf-8') as f:
    f.write(current)

print("\nAll patches applied!")

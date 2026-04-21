import codecs
import re

backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()

# Extract each missing function from backup
missing_fns = [
    'applySevResultUI', 'buildAndGotoTodayTraining', 'getLevelInfo',
    'getMicStream', 'openTodayExSingle', 'pickRandom', 'renderDomainResult',
    'renderTodayTraining', 'scoreLevel', 'startSttTimer', 'startTodayTraining',
    'startTpRecorderWord', 'submitToBackend'
]

extracted = {}
for fn_name in missing_fns:
    pattern = re.compile(r'(function\s+' + fn_name + r'\s*\([^)]*\)\s*\{)', re.DOTALL)
    m = pattern.search(backup)
    if m:
        # Extract full function using brace matching
        start = m.start()
        brace_count = 0
        idx_end = -1
        for i in range(start, len(backup)):
            if backup[i] == '{':
                brace_count += 1
            elif backup[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    idx_end = i + 1
                    break
        if idx_end != -1:
            extracted[fn_name] = backup[start:idx_end]
            print(f"Extracted: {fn_name} ({idx_end - start} chars)")
        else:
            print(f"Failed to extract: {fn_name}")
    else:
        print(f"NOT FOUND in backup: {fn_name}")

# Save all extracted functions to a snippet file
with codecs.open(r'D:\이음\prototype\missing_functions.js', 'w', 'utf-8') as f:
    f.write("// ====== MISSING FUNCTIONS FROM BACKUP ======\n\n")
    for name, code in extracted.items():
        f.write(f"// --- {name} ---\n")
        f.write(code)
        f.write("\n\n")

print("\nAll extracted. Saved to missing_functions.js")

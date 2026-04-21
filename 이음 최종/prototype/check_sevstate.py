import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Check sevState has audioBlobs initialized
idx = text.find('sevState')
# Find declaration
decl = re.search(r'let\s+sevState\s*=\s*\{.*?\};', text, flags=re.DOTALL)
if decl:
    print("sevState declaration:")
    print(decl.group(0)[:500].encode('cp949', 'replace').decode('cp949'))
else:
    print("sevState not declared with 'let'")
    # Try 'const' or 'var'
    for kw in ['const sevState', 'var sevState']:
        if kw in text:
            idx2 = text.find(kw)
            print(f"Found '{kw}' at {idx2}:")
            print(text[idx2:idx2+300].encode('cp949', 'replace').decode('cp949'))

import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Check if globalStream is declared
idx = text.find('globalStream')
start = max(0, idx - 30)
print("globalStream first occurrence:")
print(text[start:idx+80].encode('cp949', 'replace').decode('cp949'))

# Extract full getMicStream
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

fn = extract_fn(text, 'getMicStream')
print("\n=== Full getMicStream ===")
print(fn.encode('cp949', 'replace').decode('cp949'))

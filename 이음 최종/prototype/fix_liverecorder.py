import codecs
import re

path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# Find the second instance of class LiveRecorder
matches = list(re.finditer(r'class LiveRecorder\s*\{', text))
if len(matches) > 1:
    idx_start = matches[1].start()
    
    # Simple brace matching to find the end of the class
    brace_count = 0
    in_class = False
    idx_end = -1
    for i in range(idx_start, len(text)):
        if text[i] == '{':
            in_class = True
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if in_class and brace_count == 0:
                idx_end = i + 1
                break
                
    if idx_end != -1:
        text = text[:idx_start] + text[idx_end:]
        with codecs.open(path, 'w', 'utf-8') as f:
            f.write(text)
        print("Removed the duplicate LiveRecorder class successfully!")
    else:
        print("Failed to match closing brace.")
else:
    print("Did not find 2 instances.")

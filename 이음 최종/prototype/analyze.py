import re

def analyze(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"--- Analysis for {path} ---")
    sections = re.findall(r'<div[^>]*class=[\'"]?screen[^\'"]*[\'"]?[^>]*>', text)
    for s in sections:
        print(s)

analyze(r'D:\이음\prototype\therapy_ui_v4.html')
analyze(r'D:\이음\prototype\therapy_ui_v4_newui_base.html')

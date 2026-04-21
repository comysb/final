import codecs

path_base = r'D:\이음\prototype\therapy_ui_v4_newui_base.html'
path_target = r'D:\이음\prototype\therapy_ui_v4.html'

with codecs.open(path_base, 'r', 'utf-8') as f:
    base_text = f.read()

with codecs.open(path_target, 'r', 'utf-8') as f:
    target_text = f.read()

def get_block(text, start_marker, end_marker):
    start_idx = text.find(start_marker)
    if start_idx == -1: return None
    end_idx = text.find(end_marker, start_idx)
    if end_idx == -1: return None
    return text[start_idx:end_idx]

# 1. Extract screen-run CSS from base
css_block = get_block(base_text, "/* ══ NEW SCREEN 4 — Exercise Execution ══════════════════ */", "/* ══════════════════════════════════════════════════════════\n       SCREEN 5 — 결과")

# 2. Extract screen-run HTML from base
html_block = get_block(base_text, '<div class="screen off" id="screen-run">', '<div class="screen off" id="screen-result">')
if html_block:
    # Remove the trailing whitespace before the next div
    html_block = html_block.rstrip()

# 3. Extract JS logic from base
# In base, where does the task logic start?
# Usually after the global variables: let curPitchId ... or function runPitchCycle
# Let's search for the big block of phases.
js_start = base_text.find('// ── 훈련 진행 및 캔버스 관련 ────────────────────────────────')
if js_start == -1:
    js_start = base_text.find('function runPitchCycle')
js_end = base_text.find('// ── MOCK WS (삭제 예정) ────────────────────────────────')
if js_end == -1:
    js_end = base_text.find('class LiveRecorder') # If it exists?
if js_end == -1:
    js_end = base_text.find('function startMockTimer')
    
js_block = None
if js_start != -1 and js_end != -1:
    # Backtrack to the start of the section if there's a comment block
    js_start_real = base_text.rfind('//', 0, js_start) if base_text.rfind('//', 0, js_start) > js_start - 100 else js_start
    js_block = base_text[js_start_real:js_end]


print("CSS Block Length:", len(css_block) if css_block else 'None')
print("HTML Block Length:", len(html_block) if html_block else 'None')
print("JS Block Length:", len(js_block) if js_block else 'None')

if css_block and html_block and js_block:
    with codecs.open('D:/이음/prototype/extract_blocks.txt', 'w', 'utf-8') as f:
        f.write("=== CSS ===\n")
        f.write(css_block)
        f.write("\n=== HTML ===\n")
        f.write(html_block)
        f.write("\n=== JS ===\n")
        f.write(js_block)
    print("Extracted to extract_blocks.txt")

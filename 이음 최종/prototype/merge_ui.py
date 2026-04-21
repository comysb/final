import codecs
import re

path_base = r'D:\이음\prototype\therapy_ui_v4_newui_base.html'  # rehab_app code (has 16 tasks UI)
path_target = r'D:\이음\prototype\therapy_ui_v4.html'           # unified code (has diagnosis, RPPG, but simplified 16 tasks)
path_output = r'D:\이음\prototype\therapy_ui_v4_merged.html'

with codecs.open(path_base, 'r', 'utf-8') as f:
    base_text = f.read()

with codecs.open(path_target, 'r', 'utf-8') as f:
    target_text = f.read()

# 1. Extract CSS for 16 tasks from base
# Start: "/* ══ NEW SCREEN 4"
# End: "/* ══════════════════════════════════════════════════════════" under "SCREEN 5"
try:
    s_css = base_text.find("/* ══ NEW SCREEN 4")
    e_css = base_text.find("/* ════════════════════════════════", s_css + 50)
    css_patch = base_text[s_css:e_css]
    
    # In target, replace the corresponding CSS section
    s_t_css = target_text.find("/* ══ NEW SCREEN 4")
    e_t_css = target_text.find("/* ════════════════════════════════", s_t_css + 50)
    if s_t_css != -1 and e_t_css != -1:
        target_text = target_text[:s_t_css] + css_patch + target_text[e_t_css:]
except Exception as e:
    print("CSS Error:", e)

# 2. Extract HTML screen-run from base
try:
    s_html = base_text.find('<div class="screen off" id="screen-run">')
    e_html = base_text.find('<div class="screen off" id="screen-result">', s_html)
    html_patch = base_text[s_html:e_html]
    
    # In target, replace the corresponding HTML section
    s_t_html = target_text.find('<div class="screen off" id="screen-run">')
    e_t_html = target_text.find('<div class="screen off" id="screen-result">', s_t_html)
    if s_t_html != -1 and e_t_html != -1:
        target_text = target_text[:s_t_html] + html_patch + target_text[e_t_html:]
except Exception as e:
    print("HTML Error:", e)


# 3. JS extraction
# Find where JS logic of tasks begin inside base
try:
    # Look for "function runPitchCycle" in base and backtrack till we find "function startTask" or similar.
    # Actually, the easiest way is to find "// ── 화면 이동 및 초기화" or "// ── MOCK WS"
    s_js = base_text.find('// ── 훈련 진행 및 캔버스 관련')
    if s_js == -1: s_js = base_text.find('function runPitchCycle')
    
    # End JS before Mock WS or document.addEventListener('DOMContentLoaded'
    e_js = base_text.find('// ── MOCK WS')
    if e_js == -1: e_js = base_text.find("class LiveRecorder")
    if e_js == -1: e_js = base_text.find("document.addEventListener('DOMContentLoaded'")
    if e_js == -1: e_js = base_text.find('</script>', s_js)
    
    js_patch = base_text[s_js:e_js]

    # Target finding corresponding JS
    s_t_js = target_text.find('// ── 훈련 진행 및 캔버스 관련')
    if s_t_js == -1: s_t_js = target_text.find('function runPitchCycle')
    
    e_t_js = target_text.find('class LiveRecorder', s_t_js)
    if e_t_js == -1: e_t_js = target_text.find('// ── MOCK WS', s_t_js)
    if e_t_js == -1: e_t_js = target_text.find("document.addEventListener('DOMContentLoaded'", s_t_js)
    if e_t_js == -1: e_t_js = target_text.find('</script>', s_t_js)
    
    if s_t_js != -1 and e_t_js != -1:
        # Avoid removing my class LiveRecorder
        if 'LiveRecorder' in target_text[e_t_js:e_t_js+200]:
            pass
        target_text = target_text[:s_t_js] + js_patch + target_text[e_t_js:]
except Exception as e:
    print("JS Error:", e)

with codecs.open(path_output, 'w', 'utf-8') as f:
    f.write(target_text)
print("Merge complete! Saved to therapy_ui_v4_merged.html")

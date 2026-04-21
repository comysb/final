import re

# Read files
with open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', encoding='utf-8') as f:
    old_html = f.read()

with open(r'D:\이음\prototype\therapy_ui_v4_newui_base.html', 'r', encoding='utf-8') as f:
    new_base = f.read()

# 1. Extract screen-run from new_base
m_scr = re.search(r'(<div class="screen off" id="screen-run">.*?</div>\n    <!-- ══════════════════════════════════════════════════════════\n       SCREEN 5 — 결과)', new_base, flags=re.DOTALL)
if not m_scr:
    m_scr = re.search(r'(<div class="screen off" id="screen-run">.*?)(?=\n    <!-- ════════════════════════════════════════)', new_base, flags=re.DOTALL)

screen_run_chunk = m_scr.group(1)

# 2. Extract CSS for the new UI
m_css = re.search(r'/\* ══ NEW SCREEN 4 — Exercise Execution ══════════════════ \*/.*?(?=/\* ══════════════════════════════════════════════════════════\n       SCREEN 5 — 결과)', new_base, flags=re.DOTALL)
css_chunk = m_css.group(0) if m_css else ""

# 3. Extract JS logic for the phases
# The JS logic in new_base starts around phase functions or variables...
m_js = re.search(r'(let curPitchId = null;.*?)(?=function continuePitch)', new_base, flags=re.DOTALL)
# Actually, the entire JS section for rendering, let's grab everything inside <script> that is related to tasks from new_base.
# Since it's complicated, maybe we can just replace the old_html's DOM and then find what JS needs to be replaced.

print(f"Screen run chunk length: {len(screen_run_chunk)}")
print(f"CSS chunk length: {len(css_chunk)}")

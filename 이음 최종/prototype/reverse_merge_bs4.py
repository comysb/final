from bs4 import BeautifulSoup
import codecs
import re

path_base = r'D:\rehab_app\templates\index.html'
path_v4 = r'D:\이음\prototype\therapy_ui_v4.html'
path_out = r'D:\이음\prototype\therapy_ui_v4_perfect.html'

with codecs.open(path_base, 'r', 'utf-8') as f:
    html_base = f.read()

with codecs.open(path_v4, 'r', 'utf-8') as f:
    html_v4 = f.read()

soup_base = BeautifulSoup(html_base, 'html.parser')
soup_v4 = BeautifulSoup(html_v4, 'html.parser')

def extract_css(html, start_marker, end_marker):
    s = html.find(start_marker)
    if s == -1: return ""
    e = html.find(end_marker, s)
    if e == -1: return ""
    return html[s:e]

# 1. HTML 주입 (폰 껍데기 안에 screen들을 모두 병합)
phone_base = soup_base.find(id='phone')

# 기존 v4에서 rehab_app에 없는 진단 관련 스크린만 추출
screens_to_keep = ['screen-splash', 'screen-setup', 'screen-eum', 'screen-home', 'screen-rppg', 'screen-severity', 'screen-tasks', 'screen-domain-result', 'screen-today-training', 'screen-all-ex']

# base에 있는 기존 스크린 목록
base_screen_ids = [s.get('id') for s in phone_base.find_all('div', class_=re.compile('screen')) if s.get('id')]

# phone_base를 비우지 않고, base_screen_ids에 포함된 것들은 남기되, v4에서 가져온 것들과 합침.
# 간단히 말해, v4에서 온 것들을 쭉 먼저 넣고, base의 screen-run, screen-result를 뒤에 붙이는 방식을 취하거나,
# 기존 phone_base의 자식 요소들을 교체한다.
new_phone_children = []
for sid in ['screen-splash', 'screen-setup', 'screen-eum', 'screen-home', 'screen-rppg', 'screen-severity', 'screen-domain-result', 'screen-today-training', 'screen-tasks', 'screen-all-ex']:
    scr = soup_v4.find(id=sid)
    if scr: new_phone_children.append(scr)

for sid in ['screen-run', 'screen-result']:
    scr = soup_base.find(id=sid)
    if scr: new_phone_children.append(scr)

phone_base.clear()
for child in new_phone_children:
    phone_base.append(child)


# 2. CSS 주입 (기존 진단 CSS 뽑아오기)
css_malgil = extract_css(html_v4, "/* ── 중증도 진단 화면 ── */", "/* ══ NEW SCREEN 4")

# style 태그 맨 뒤에 붙이기
style_tag = soup_base.find('style')
if style_tag and css_malgil:
    style_tag.append("\n" + css_malgil + "\n")


# 3. JS 주입
# v4 JS 중에서 LiveRecorder 클래스와 진단 로직을 몽땅 뽑아온다.
# v4의 JS 태그 안에서 LiveRecorder ~ _applyLive 까지 가져오고, 진단함수들도 가져오기
# 좀 더 정밀하게 정규식이나 마커로 자름.
js_malgil = extract_css(html_v4, "const TASK_TYPE_MAP", "// ── 화면 이동 및 초기화 ────────────────────────────────")
js_recorder = extract_css(html_v4, "class LiveRecorder", "/*  ε  */")
if not js_recorder:
    js_recorder = extract_css(html_v4, "class LiveRecorder", "function loadExerciseVideo")

script_tag = soup_base.find('script')
if script_tag:
    old_script = script_tag.string or ""
    # Inject MockWS disable:
    old_script = old_script.replace('pitchIv = setInterval(() => {', 'pitchIv = setInterval(() => { return;')
    old_script = old_script.replace('volIv = setInterval(() => {', 'volIv = setInterval(() => { return;')
    
    script_tag.string = "\n" + (js_malgil or "") + "\n\n" + (js_recorder or "") + "\n\n" + old_script


with codecs.open(path_out, 'w', 'utf-8') as f:
    f.write(str(soup_base))

print("Reverse merge complete! Check therapy_ui_v4_perfect.html")

import codecs
import re

current_path = r'D:\이음\prototype\therapy_ui_v4.html'
backup_path = r'D:\이음\이음복사본\prototype\therapy_ui_v4.html'

with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

with codecs.open(backup_path, 'r', 'utf-8') as f:
    backup = f.read()

# 1. Replace sevState initialization to include audioBlobs with correct structure
old_sev_state = 'let sevState = {taskIdx:0, step:0, recording:false, timer:null, waveTimer:null, sec:0, done:[false,false,false], audioBlobs:[null,null,null]};'
new_sev_state = 'let sevState = {taskIdx:0, step:0, recording:false, timer:null, waveTimer:null, sec:0, done:[false,false,false]};\nlet audioBlobs = { vowels: [], putterker: null, words: [], noise: null, currentStep: 0 };'
current = current.replace(old_sev_state, new_sev_state)

# 2. Fix showSevComplete to call submitToBackend (not doSevAnalysis) 
old_show = re.search(r'function showSevComplete\(\)\s*\{.*?\}', current, flags=re.DOTALL)
if old_show:
    new_show = """function showSevComplete() {
  // Hide rec and list views
  document.getElementById('sev-rec-view').style.display = 'none';
  document.getElementById('sev-list-view').style.display = 'none';

  // Show the complete container
  document.getElementById('sev-complete-view').style.display = 'flex';

  // Show spinner (analyzing), hide result
  const analyzingView = document.getElementById('sev-analyzing-view');
  const resultView    = document.getElementById('sev-result-view');
  if (analyzingView) analyzingView.style.display = 'flex';
  if (resultView)    resultView.style.display    = 'none';

  // Call the unified backend submission (uses audioBlobs properly)
  submitToBackend();
}"""
    current = current[:old_show.start()] + new_show + current[old_show.end():]
    print("Fixed showSevComplete to call submitToBackend")
else:
    print("showSevComplete not found - brace matching...")
    idx = current.find('function showSevComplete()')
    if idx != -1:
        brace_count = 0
        started = False
        idx_end = -1
        for i in range(idx, len(current)):
            if current[i] == '{':
                started = True
                brace_count += 1
            elif current[i] == '}':
                brace_count -= 1
                if started and brace_count == 0:
                    idx_end = i + 1
                    break
        if idx_end != -1:
            new_show = """function showSevComplete() {
  document.getElementById('sev-rec-view').style.display = 'none';
  document.getElementById('sev-list-view').style.display = 'none';
  document.getElementById('sev-complete-view').style.display = 'flex';
  const analyzingView = document.getElementById('sev-analyzing-view');
  const resultView    = document.getElementById('sev-result-view');
  if (analyzingView) analyzingView.style.display = 'flex';
  if (resultView)    resultView.style.display    = 'none';
  submitToBackend();
}"""
            current = current[:idx] + new_show + current[idx_end:]
            print("Fixed showSevComplete via brace matching!")

# 3. Fix submitToBackend to update UI correctly
old_submit = re.search(r'async function submitToBackend\(\)\s*\{.*?\}(?=\s*\n)', current, flags=re.DOTALL)
new_submit = """async function submitToBackend() {
  try {
    const fd = new FormData();
    if (audioBlobs.noise)      fd.append('noise_file', audioBlobs.noise,      'noise.webm');
    if (audioBlobs.putterker)  fd.append('putterker',  audioBlobs.putterker,  'putterker.webm');

    if (audioBlobs.vowels[0]) fd.append('vowel_a', audioBlobs.vowels[0], 'vowel_a.webm');
    if (audioBlobs.vowels[1]) fd.append('vowel_i', audioBlobs.vowels[1], 'vowel_i.webm');
    if (audioBlobs.vowels[2]) fd.append('vowel_u', audioBlobs.vowels[2], 'vowel_u.webm');

    audioBlobs.words.forEach((w) => {
       fd.append('word_files', w.blob, w.word + '.webm');
    });
    fd.append('word_sex', 'M');
    fd.append('word_age', 50);

    const res  = await fetch('http://localhost:8000/api/predict', { method: 'POST', body: fd });
    const data = await res.json();
    console.log('[진단 결과]', data);

    if (data.status === 'success') {
      const cls = data.severity_class !== undefined ? data.severity_class : 0;
      applySevResultUI(cls);
      window._lastDomainData = data;
    } else {
      console.warn('[API 실패]', data);
      applySevResultUI(0);
    }
  } catch(e) {
    console.warn('[submitToBackend 오류]', e);
    applySevResultUI(0);
  }
}

"""

if old_submit:
    current = current[:old_submit.start()] + new_submit + current[old_submit.end():]
    print("Replaced submitToBackend")
else:
    # brace match
    idx = current.find('async function submitToBackend()')
    if idx != -1:
        brace_count = 0
        started = False
        idx_end = -1
        for i in range(idx, len(current)):
            if current[i] == '{':
                started = True
                brace_count += 1
            elif current[i] == '}':
                brace_count -= 1
                if started and brace_count == 0:
                    idx_end = i + 1
                    break
        if idx_end != -1:
            current = current[:idx] + new_submit + current[idx_end:]
            print("Replaced submitToBackend via brace match!")
    else:
        print("submitToBackend not found!")

# Also reset audioBlobs when starting the severity screen
if "audioBlobs = { vowels: [], putterker: null, words: [], noise: null, currentStep: 0 };" not in current:
    # Add reset in resetSeverity if it exists
    reset_idx = current.find('function resetSeverity')
    if reset_idx != -1:
        current = current[:reset_idx+current[reset_idx:].find('{')+1] + '\n  audioBlobs = { vowels: [], putterker: null, words: [], noise: null, currentStep: 0};' + current[reset_idx+current[reset_idx:].find('{')+1:]
        print("Added audioBlobs reset to resetSeverity")

with codecs.open(current_path, 'w', 'utf-8') as f:
    f.write(current)

print("\nAll fixes applied!")

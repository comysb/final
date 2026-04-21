import codecs
import re

current_path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Replace doSevAnalysis with a version that uses submitToBackend-compatible call
# This sends ALL 3 task recordings as one unified request to /api/predict
new_do_sev = """async function doSevAnalysis() {
  try {
    const fd = new FormData();
    
    // sevState.audioBlobs[0] = putterker (DDK task)
    // sevState.audioBlobs[1] = vowel (아이우 task) - but we need a/i/u separately
    // sevState.audioBlobs[2] = word files (단어 task)
    // For now, map: blob[0]=putterker, blob[1]=vowel_a, blob[2]=word
    
    if (sevState.audioBlobs[0]) {
      fd.append('putterker', sevState.audioBlobs[0], 'putterker.webm');
    }
    // Vowels - if we recorded blob[1] as vowel_a, send it as vowel_a/i/u all same
    if (sevState.audioBlobs[1]) {
      fd.append('vowel_a', sevState.audioBlobs[1], 'vowel_a.webm');
      fd.append('vowel_i', sevState.audioBlobs[1], 'vowel_i.webm');
      fd.append('vowel_u', sevState.audioBlobs[1], 'vowel_u.webm');
    }
    // Word files - if audioBlobs has wordBlobs, append them
    if (sevState.wordBlobs && sevState.wordBlobs.length > 0) {
      sevState.wordBlobs.forEach(w => {
        fd.append('word_files', w.blob, w.word + '.webm');
      });
      fd.append('word_sex', 'M');
      fd.append('word_age', 50);
    } else if (sevState.audioBlobs[2]) {
      // fallback: use blob[2] as a word file
      fd.append('word_files', sevState.audioBlobs[2], '나무.webm');
      fd.append('word_sex', 'M');
      fd.append('word_age', 50);
    }

    const resp = await fetch('http://localhost:8000/api/predict', {
      method: 'POST',
      body: fd
    });

    if (!resp.ok) {
      console.warn('API error:', resp.status);
      renderSevResult([null, null, null]);
      return;
    }

    const data = await resp.json();
    console.log('[분석 결과]', data);

    if (data.status === 'success') {
      // Use the final_class from backend directly
      const cls = data.severity_class !== undefined ? data.severity_class : 0;
      applySevResultUI(cls);

      // Store domain scores for domain result screen
      window._lastDomainData = data;
    } else {
      console.warn('[API] 분석 실패:', data);
      renderSevResult([null, null, null]);
    }

  } catch(e) {
    console.warn('[doSevAnalysis] 오류:', e);
    // Fallback: show UI with class 0 (정상) as default
    applySevResultUI(0);
  }
}

"""

# Replace the existing doSevAnalysis function
old_pattern = re.compile(r'async function doSevAnalysis\(\)\s*\{.*?\}(?=\s*\n)', re.DOTALL)
m = old_pattern.search(current)
if m:
    current = current[:m.start()] + new_do_sev + current[m.end():]
    print("Replaced doSevAnalysis with proper backend call!")
else:
    # Try again with greedy brace matching
    idx = current.find('async function doSevAnalysis()')
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
            current = current[:idx] + new_do_sev + current[idx_end:]
            print("Replaced via brace matching!")
        else:
            print("Failed to match end brace")
    else:
        print("doSevAnalysis not found!")

with codecs.open(current_path, 'w', 'utf-8') as f:
    f.write(current)

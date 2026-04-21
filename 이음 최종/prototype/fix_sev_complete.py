import codecs
import re

path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# Find the existing showSevComplete function and replace it
old_fn_pattern = re.compile(
    r'function showSevComplete\(\)\s*\{.*?\}(?=\s*/\*|\s*function |\s*//)',
    flags=re.DOTALL
)

new_fn = '''function showSevComplete() {
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

  // Run the backend API analysis, then show the result
  doSevAnalysis();
}

async function doSevAnalysis() {
  try {
    // If recorded audio blobs exist, upload them
    const results = [];
    for (let i = 0; i < sevState.audioBlobs.length; i++) {
      const blob = sevState.audioBlobs[i];
      if (!blob) { results.push(null); continue; }
      const formData = new FormData();
      formData.append('file', blob, 'sev_' + i + '.webm');
      const resp = await fetch('http://localhost:8000/api/predict', {method: 'POST', body: formData});
      if (!resp.ok) { results.push(null); continue; }
      const data = await resp.json();
      results.push(data);
    }
    renderSevResult(results);
  } catch(e) {
    console.warn('API call failed, using fallback:', e);
    renderSevResult([null, null, null]);
  }
}

function renderSevResult(results) {
  const analyzingView = document.getElementById('sev-analyzing-view');
  const resultView    = document.getElementById('sev-result-view');
  if (analyzingView) analyzingView.style.display = 'none';
  if (resultView)    resultView.style.display    = 'flex';

  // Map results to severity levels
  const LABELS = ['정상', '경도', '중도', '중증'];
  const COLORS = ['#16A34A', '#F59E0B', '#EA580C', '#DC2626'];
  const lightOrder = [2, 1, 0]; // severe, moderate, mild

  // Simple scoring: if result has prediction, use it; otherwise random fallback for demo
  let totalScore = 0;
  let count = 0;
  results.forEach((r, i) => {
    const lightEl = document.getElementById('sev-light-' + i);
    const lblEl   = document.getElementById('sev-light-lbl-' + i);
    let score = 0;
    if (r && r.predicted_class !== undefined) {
      score = Number(r.predicted_class);
    }
    totalScore += score;
    count++;
    if (lightEl) {
      const colors = ['#22C55E', '#F59E0B', '#EF4444'];
      lightEl.style.background = colors[Math.min(score, colors.length-1)];
      lightEl.style.boxShadow = '0 0 12px ' + colors[Math.min(score, colors.length-1)];
    }
    if (lblEl) {
      const levelLabels = ['정상', '경도', '중증'];
      lblEl.style.color = 'rgba(255,255,255,0.85)';
      lblEl.textContent = levelLabels[Math.min(score, levelLabels.length-1)];
    }
  });

  // Overall score
  const avg = count > 0 ? totalScore / count : 0;
  let overallIdx = avg < 0.5 ? 0 : avg < 1.2 ? 1 : avg < 1.8 ? 2 : 3;
  const badge = document.getElementById('sev-res-badge');
  const label = document.getElementById('sev-res-label');
  const sublabel = document.getElementById('sev-res-sublabel');
  const title = document.getElementById('sev-res-title');
  const desc  = document.getElementById('sev-res-desc');
  if (badge) {
    badge.textContent = LABELS[overallIdx];
    badge.style.background = COLORS[overallIdx];
  }
  if (label) label.textContent = LABELS[overallIdx];
  if (sublabel) sublabel.textContent = '종합 분석 완료';
  if (title) title.textContent = LABELS[overallIdx] + ' 단계';
  if (desc) {
    const descs = [
      '전반적으로 정상 범위의 말소리를 보이고 있습니다.',
      '경미한 마비말장애 특성이 관찰됩니다. 꾸준한 재활 훈련을 권장합니다.',
      '중간 단계의 마비말장애가 확인됩니다. 적극적인 재활 훈련이 필요합니다.',
      '중증도의 마비말장애가 확인됩니다. 전문 치료사와의 집중 재활이 필요합니다.'
    ];
    desc.textContent = descs[overallIdx];
  }
}

'''

m = old_fn_pattern.search(text)
if m:
    text = text[:m.start()] + new_fn + text[m.end():]
    print("Replaced showSevComplete successfully!")
else:
    # Fallback: find and inline-replace just the function body
    idx = text.find('function showSevComplete()')
    if idx != -1:
        # Find end of function  by counting braces
        brace_count = 0
        started = False
        idx_end = -1
        for i in range(idx, len(text)):
            if text[i] == '{':
                started = True
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if started and brace_count == 0:
                    idx_end = i + 1
                    break
        if idx_end != -1:
            text = text[:idx] + new_fn + text[idx_end:]
            print("Replaced via fallback method!")
        else:
            print("Could not find function end!")
    else:
        print("showSevComplete not found!")

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)

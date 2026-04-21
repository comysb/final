import codecs

path = r'D:\이음\prototype\therapy_ui_v4_perfect.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# 1. Update startTask to call startRealtimeSession
patch_task = '''
  const PITCH_EX = [4, 5, 6];
  if (PITCH_EX.includes(id)) {
    if(window._liveRecorder) window._liveRecorder.stop();
    startRealtimeSession(id, Object.assign({}, METRICS[id] || METRICS['mini']));
    startPitchGuide(id);
    return;
  }
  const VOLUME_EX = [7, 8];
  if (VOLUME_EX.includes(id)) {
    if(window._liveRecorder) window._liveRecorder.stop();
    startRealtimeSession(id, Object.assign({}, METRICS[id] || METRICS['mini']));
    startVolumeGuide(id);
    return;
  }
  const BREATH_EX = [9, 12];
  if (BREATH_EX.includes(id)) {
    if(window._liveRecorder) window._liveRecorder.stop();
    startRealtimeSession(id, Object.assign({}, METRICS[id] || METRICS['mini']));
    startBreathGuide(id);
    return;
  }
'''

idx = text.find('// 2. 음도/강도/조음 등 나머지 훈련 연결')
if idx != -1:
    text = text[:idx] + patch_task + "\n  " + text[idx:]


# 2. Add fixed _applyLive function
patch_live = '''
function _applyLive(taskId, liveData, metrics) {
  // === 호흡 ===
  if (document.getElementById('phase-breath') && document.getElementById('phase-breath').style.display === 'block') {
    const val = liveData.current_db || 0;
    const tgt = document.querySelector('#phase-breath .ring-fill');
    if (tgt) {
      let pct = ((val - 20) / (95 - 20)) * 100;
      pct = Math.max(0, Math.min(100, pct));
      const dash = 200 * Math.PI;
      tgt.style.strokeDasharray = dash;
      tgt.style.strokeDashoffset = dash - (dash * (pct / 100));
      const valEl = document.querySelector('#phase-breath .ring-val');
      if (valEl) valEl.textContent = Math.round(val);
    }
  }

  // === 피치 (음도) ===
  function updatePitchUI() {
      const f0 = liveData.f0 || 0;
      const isVd = liveData.voiced || false;
      const hzLabel = document.getElementById('pitch-hz');
      const dot = document.getElementById('pitch-dot');
      const pulse = document.getElementById('pitch-dot-pulse');
      
      if (!isVd || f0 < 50) {
        if(hzLabel) hzLabel.textContent = '--- Hz';
        if(dot) dot.style.fill = '#CBD5E1';
      } else {
        if(hzLabel) hzLabel.textContent = Math.round(f0) + ' Hz';
        if(dot) dot.style.fill = '#16A34A';
        
        const canvas = document.getElementById('pitch-canvas');
        if (canvas && dot) {
           const min = 80, max = 300;
           let norm = (f0 - min) / (max - min);
           norm = Math.max(0, Math.min(1, norm));
           const y = 300 - (norm * 300);
           dot.setAttribute('cy', y);
           pulse.setAttribute('cy', y);
        }
      }
  }
  
  if (document.getElementById('phase-pitch') && document.getElementById('phase-pitch').style.display === 'block') {
      updatePitchUI();
  }
  if (document.getElementById('phase-a') && document.getElementById('phase-a').style.display === 'block') {
      updatePitchUI();
  }
  
  // === 볼륨 ===
  if (document.getElementById('phase-volume') && document.getElementById('phase-volume').style.display === 'block') {
     const db = liveData.current_db || 0;
     const userBar = document.getElementById('volume-user');
     if(userBar) {
       let pct = ((db - 20)/(95 - 20)) * 100;
       userBar.style.height = Math.max(5, Math.min(100, pct)) + '%';
     }
  }
}
'''

# Find a safe place to insert _applyLive (e.g., before LiveRecorder)
idx2 = text.find('class LiveRecorder')
if idx2 != -1:
    text = text[:idx2] + patch_live + "\n" + text[idx2:]

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)

print("Final patch complete on perfect file.")

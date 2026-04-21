import codecs

path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# Fix _applyLive signature
idx = text.find('function _applyLive(liveData) {')
if idx != -1:
    end_idx = text.find('// End _applyLive', idx)
    patch_live = '''function _applyLive(taskId, liveData, metrics) {
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
      document.querySelector('#phase-breath .ring-val').textContent = val;
    }
  }

  // === 피치 (음도내리기 등) ===
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
           const maxY = window.pitchSvgHeight ? window.pitchSvgHeight : 300;
           const y = maxY - (norm * maxY);
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
    text = text[:idx] + patch_live + "\n// End _applyLive" + text[end_idx + len('// End _applyLive'):]

    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(text)
    print("Fixed _applyLive arguments!")
else:
    print("Could not find _applyLive")

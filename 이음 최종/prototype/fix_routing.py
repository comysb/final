import codecs

path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

patch_routing = """
// ── 화면 이동 및 초기화 ────────────────────────────────
function goto(sid) {
  const sc = document.querySelectorAll('.screen');
  sc.forEach(s => s.classList.add('off'));
  const t = document.getElementById('screen-' + sid);
  if (t) t.classList.remove('off');
  
  if (sid === 'run') {
    // Navigating into run
  } else {
    // Navigated away from run
    if(typeof stopAllRecorders === 'function') stopAllRecorders();
  }
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', () => {
  const h = location.hash.replace('#', '') || 'splash';
  if (['splash','setup','eum','home','rppg','severity','domain-result','today-training','tasks','all-ex','run','result'].includes(h)) {
    goto(h);
    if(h === 'tasks' && typeof renderTasks === 'function') renderTasks();
    if(h === 'all-ex' && typeof renderAllEx === 'function') renderAllEx();
    if(h === 'today-training' && typeof buildAndGotoTodayTraining === 'function') buildAndGotoTodayTraining();
    if(h === 'severity' && typeof renderSevList === 'function') {
       renderSevList();
    }
  } else {
    goto('splash');
  }
});

window.addEventListener('DOMContentLoaded', () => {
  const h = location.hash.replace('#', '');
  if (h) {
      window.dispatchEvent(new Event('hashchange'));
  } else {
      setTimeout(() => location.hash = 'setup', 2000);
      goto('splash');
  }
});
"""

idx1 = text.find('// ── 화면 이동 및 초기화')
if idx1 != -1:
    idx2 = text.find('});', text.find('DOMContentLoaded', idx1))
    if idx2 != -1:
        text = text[:idx1] + patch_routing + text[idx2+3:]
else:
    # If the marker wasn't found, just append to the script block.
    # Searching for the last script tag could be risky, but let's try.
    idx3 = text.rfind('</script>')
    if idx3 != -1:
        text = text[:idx3] + patch_routing + "\n" + text[idx3:]

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)

print("Routing fixed!")

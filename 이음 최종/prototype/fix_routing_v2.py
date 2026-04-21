import codecs
import re

path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# 1. Remove the FIRST goto(id) block
pattern_goto1 = re.compile(r'function goto\([a-zA-Z0-9]+\)\s*\{[^\}]*\}[^\}]*\}', re.DOTALL)
# Wait, goto(id) has an inner bracket? No, it's just multiple lines.
# Let's cleanly replace the literal text we found earlier for the first goto:
first_goto_literal = """function goto(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.add('off'));
  document.getElementById('screen-' + id).classList.remove('off');
  stopRecTimer();
  if (id === 'tasks')     renderTasks();
  if (id === 'all-ex')   renderAllEx();
  if (id === 'result')   renderResult();
  if (id === 'rppg')     resetRppg();
  if (id === 'severity') resetSeverity();
}"""
text = text.replace(first_goto_literal, "")

# 2. Re-write the second goto to encompass everything
new_routing_block = """
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
  
  if(typeof stopRecTimer === 'function') stopRecTimer();
  if (sid === 'tasks' && typeof renderTasks === 'function') renderTasks();
  if (sid === 'all-ex' && typeof renderAllEx === 'function') renderAllEx();
  if (sid === 'result' && typeof renderResult === 'function') renderResult();
  if (sid === 'rppg' && typeof resetRppg === 'function') resetRppg();
  if (sid === 'severity' && typeof resetSeverity === 'function') resetSeverity();

  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', () => {
  const h = location.hash.replace('#', '') || 'splash';
  if (['splash','setup','eum','home','rppg','severity','domain-result','today-training','tasks','all-ex','run','result'].includes(h)) {
    goto(h);
    if(h === 'today-training' && typeof buildAndGotoTodayTraining === 'function') buildAndGotoTodayTraining();
    if(h === 'severity' && typeof renderSevList === 'function') renderSevList();
  } else {
    goto('splash');
  }
});

window.addEventListener('DOMContentLoaded', () => {
  const h = location.hash.replace('#', '');
  if (h) {
      window.dispatchEvent(new Event('hashchange'));
  } else {
      setTimeout(() => { if (!location.hash) location.hash = 'setup'; }, 2000);
      goto('splash');
  }
});
"""

# Find my previously injected patched routing and replace it
# "function goto(sid)" to the end of "DOMContentLoaded" listener
match_patch = re.search(r'function goto\(sid\).*?\}\);[\s]*\}\);', text, flags=re.DOTALL)
if match_patch:
    text = text[:match_patch.start()] + new_routing_block + text[match_patch.end():]
else:
    # If regex fails, let's just find goto(sid) and split
    idx_patch = text.find('function goto(sid)')
    if idx_patch != -1:
        idx_end = text.rfind('});')
        text = text[:idx_patch] + new_routing_block + text[idx_end+3:]

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)

print("Routing fixed comprehensively!")

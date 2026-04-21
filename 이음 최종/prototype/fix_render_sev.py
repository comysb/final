import codecs
import re

current_path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(current_path, 'r', 'utf-8') as f:
    current = f.read()

# Fix renderSevResult to correctly call applySevResultUI(cls) with the right class int
# First, find the current renderSevResult and replace it with a simpler correct version
old_render = re.search(r'function renderSevResult\(results\)\s*\{.*?\}(?=\s*\n)', current, flags=re.DOTALL)
if old_render:
    print("Found renderSevResult, will replace")
    new_render_sv = """function renderSevResult(results) {
  // Called after API returns - results is array of {predicted_class} or null
  let totalScore = 0;
  let count = 0;
  results.forEach((r) => {
    if (r && r.predicted_class !== undefined) {
      totalScore += Number(r.predicted_class);
      count++;
    }
  });
  const avg = count > 0 ? totalScore / count : 0;
  // Map to 3 classes: 0=normal, 1=mild/moderate, 2=severe
  let cls = avg < 0.5 ? 0 : avg < 1.5 ? 1 : 2;
  applySevResultUI(cls);
}

"""
    current = current[:old_render.start()] + new_render_sv + current[old_render.end():]
else:
    print("renderSevResult not found or pattern failed.")

# Also fix doSevAnalysis to not double-call applySevResultUI
current = current.replace(
    'renderSevResult(results);\n  applySevResultUI(results);',
    'renderSevResult(results);'
)

with codecs.open(current_path, 'w', 'utf-8') as f:
    f.write(current)

print("Fixed renderSevResult to properly call applySevResultUI!")

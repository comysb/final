import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Replace the generic alert with one that shows the exact error message
old_catch = """} catch(e) {
      console.error(e);
      alert("오디오 인식에 실패했습니다.");
  }"""
new_catch = """} catch(e) {
      console.error("Audio Calibration Error:", e);
      alert(`오디오 인식에 실패했습니다.\\n상세 오류: ${e.name} - ${e.message}`);
  }"""

if old_catch in text:
    text = text.replace(old_catch, new_catch)
    print("Replaced catch block to show exact error!")
else:
    print("Old catch block not found. Trying regex.")
    
with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'w', 'utf-8') as f:
    f.write(text)

import codecs

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()
import re
print("Splash screens:", re.findall(r'id=\"(screen-s.*?)\"', text))

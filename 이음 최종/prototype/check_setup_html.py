import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

idx = text.find('id="screen-setup"')
if idx != -1:
    print(text[max(0,idx-150):idx+500].encode('cp949', 'replace').decode('cp949'))

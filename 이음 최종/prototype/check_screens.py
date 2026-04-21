import codecs

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

idx = text.find('id="screen-setup"')
if idx != -1:
    print('Found screen-setup!')
    start = max(0, idx - 100)
    print(text[start:idx+100])
else:
    print('screen-setup NOT found! Which screens exist?')
    import re
    screens = re.findall(r'id=\"(screen-[a-zA-Z0-9-]+)\"', text)
    print(screens)

import codecs

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

idx = text.find("addEventListener('hashchange'")
if idx == -1: idx = text.find('addEventListener("hashchange"')

if idx != -1:
    with codecs.open(r'D:\이음\prototype\debug_hash.txt', 'w', 'utf-8') as out:
        out.write(text[idx:idx+1500])

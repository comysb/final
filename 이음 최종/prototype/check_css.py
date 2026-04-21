import codecs

with codecs.open(r'D:\rehab_app\templates\index.html', 'r', 'utf-8') as f:
    text1 = f.read()

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text2 = f.read()

idx1 = text1.find('<style>')
idx2 = text1.find('/* ── PROTOTYPE BAR')
if idx1 != -1 and idx2 != -1:
    css_global_base = text1[idx1:idx2]
    
idx3 = text2.find('<style>')
idx4 = text2.find('/* ── PROTOTYPE BAR')
if idx3 != -1 and idx4 != -1:
    css_global_target = text2[idx3:idx4]
    
print("CSS GLOBAL DIFF:")
if css_global_base != css_global_target:
    print("Different!")
else:
    print("Same!")

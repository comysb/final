import codecs

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Replace /static/videos/ with videos/ in VIDEO_MAP
old = "'/static/videos/"
new = "'videos/"

count = text.count(old)
text = text.replace(old, new)

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'w', 'utf-8') as f:
    f.write(text)

print(f"Fixed {count} video path(s): /static/videos/ -> videos/")

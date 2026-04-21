import codecs

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Add let globalStream = null; before the first getMicStream
old_str = "async function getMicStream() {"
new_str = "let globalStream = null;\nasync function getMicStream() {"

if old_str in text and "let globalStream" not in text:
    text = text.replace(old_str, new_str)
    print("Added let globalStream = null;")
else:
    print("globalStream already exists or async function getMicStream not found.")
    
    # Try the non-async one just in case
    old_str2 = "function getMicStream() {"
    new_str2 = "let globalStream = null;\nfunction getMicStream() {"
    if old_str2 in text and "let globalStream" not in text:
         text = text.replace(old_str2, new_str2)
         print("Added to non-async function getMicStream")

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'w', 'utf-8') as f:
    f.write(text)

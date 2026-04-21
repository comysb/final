import codecs

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Fix undeclared variables in startSevCalibration
old_block = """const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaStreamSource(stream);
    noiseAnalyser = audioCtx.createAnalyser();
    noiseAnalyser.fftSize = 256;
    source.connect(noiseAnalyser);
    noiseDataArray = new Uint8Array(noiseAnalyser.frequencyBinCount);"""

new_block = """const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaStreamSource(stream);
    const noiseAnalyser = audioCtx.createAnalyser();
    noiseAnalyser.fftSize = 256;
    source.connect(noiseAnalyser);
    const noiseDataArray = new Uint8Array(noiseAnalyser.frequencyBinCount);"""

if old_block in text:
    text = text.replace(old_block, new_block)
    print("Fixed variable declarations in startSevCalibration!")
else:
    print("Block not found!")

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'w', 'utf-8') as f:
    f.write(text)

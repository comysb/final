import codecs
import re

path = r'D:\이음\prototype\therapy_ui_v4.html'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

# 1. Add audioBlobs to sevState
old_state = 'let sevState = {taskIdx:0, step:0, recording:false, timer:null, waveTimer:null, sec:0, done:[false,false,false]};'
new_state = 'let sevState = {taskIdx:0, step:0, recording:false, timer:null, waveTimer:null, sec:0, done:[false,false,false], audioBlobs:[null,null,null]};'
text = text.replace(old_state, new_state)

# 2. Find where recording stops and blob is saved - look for MediaRecorder stop/onstop
# Find the relevant place to save audio blob when recording stops
# We need to find the recording logic and add blob saving

# Check if sevState.audioBlobs is already saved somewhere
if 'sevState.audioBlobs' in text:
    print("audioBlobs already used in code.")
else:
    print("audioBlobs NOT saved on recording. Will add blob saving...")
    # Find where the recording stop happens in severity section
    idx = text.find('sevState.recording = false')
    if idx != -1:
        print("Found recording stop at:", idx)
        print(text[max(0,idx-200):idx+200].encode('cp949', 'replace').decode('cp949'))

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)

print("Updated sevState with audioBlobs")

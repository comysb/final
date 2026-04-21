import codecs
import re
import os

# Read current VIDEO_MAP entries
with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

idx = text.find('const VIDEO_MAP')
end = text.find('};', idx) + 2
video_map_block = text[idx:end]
print("=== Current VIDEO_MAP ===")
print(video_map_block)

# List actual files in videos dir
actual_files = os.listdir(r'D:\이음\prototype\videos')
print("\n=== Actual files in videos/ ===")
for f in sorted(actual_files):
    print(f)

# Extract paths from VIDEO_MAP
paths = re.findall(r"'videos/([^']+)'", video_map_block)
print("\n=== Matching check ===")
for p in paths:
    exists = p in actual_files
    print(f"  {'OK' if exists else 'MISSING'}: {p}")

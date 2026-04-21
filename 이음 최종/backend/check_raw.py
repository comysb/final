import sys
import os

# Read the file as bytes to see exact encoding
with open(r"D:\이음복사본1\backend\main.py", "rb") as f:
    content = f.read()

# Find the target section around line 347-368
lines = content.split(b"\r\n")
for i in range(344, 372):
    try:
        print(f"{i+1}: {lines[i]!r}")
    except IndexError:
        pass

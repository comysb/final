import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

dirs = sorted(os.listdir('D:\\'))
for d in dirs:
    print(repr(d), '->', d)

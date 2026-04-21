import codecs
import re

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

# Replace SEV_WORDS_RAW
new_words = "['안녕하세요', '감사합니다', '나비', '사과', '피아노', '고양이', '자동차', '우산', '기차', '책상', '물', '바나나', '강아지', '자전거', '시계', '안전', '사랑', '가족', '친구', '병원', '의사', '간호사', '약', '시간', '날씨', '하늘', '구름', '태양', '달', '별']"
pattern = r'const SEV_WORDS_RAW\s*=\s*\[.*?\];'
text = re.sub(pattern, f'const SEV_WORDS_RAW = {new_words};', text, flags=re.DOTALL)

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'w', 'utf-8') as f:
    f.write(text)

print("Replaced SEV_WORDS_RAW with 30 words.")

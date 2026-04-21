import codecs
from bs4 import BeautifulSoup

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

soup = BeautifulSoup(text, 'html.parser')
splash = soup.find(id='screen-splash')
if splash:
    s = splash.encode('utf-8').decode('utf-8')[:300]
    print("SPLASH:\n", s.encode('cp949', 'replace').decode('cp949'))
    
setup = soup.find(id='screen-setup')
if setup:
    s = setup.encode('utf-8').decode('utf-8')[:300]
    print("SETUP:\n", s.encode('cp949', 'replace').decode('cp949'))

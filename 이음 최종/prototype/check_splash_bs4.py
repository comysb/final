import codecs
from bs4 import BeautifulSoup

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

splash = soup.find(id="screen-splash")
if splash:
    print("Classes of screen-splash:", splash.get('class'))
else:
    print("NO screen-splash FOUND!")

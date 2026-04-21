import codecs
from bs4 import BeautifulSoup

with codecs.open(r'D:\이음\prototype\therapy_ui_v4.html', 'r', 'utf-8') as f:
    text = f.read()

soup = BeautifulSoup(text, 'html.parser')

# Check what's inside sev-complete-view  
complete_view = soup.find(id='sev-complete-view')
if complete_view:
    print("=== sev-complete-view children IDs ===")
    for child in complete_view.find_all(True):
        if child.get('id'):
            print(child.get('id'))
else:
    print("sev-complete-view NOT FOUND")

# Check what's inside sev-analyzing-view
analyzing_view = soup.find(id='sev-analyzing-view')
if analyzing_view:
    print("\n=== sev-analyzing-view parent ===")
    print(analyzing_view.parent.get('id'))
else:
    print("sev-analyzing-view NOT FOUND")

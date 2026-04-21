from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument('--headless')
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=options)

driver.get('http://localhost:8080/therapy_ui_v4.html#setup')
time.sleep(2)

print("--- BROWSER CONSOLE LOGS ---")
for entry in driver.get_log('browser'):
    if entry['level'] == 'SEVERE':
        print('ERROR:', entry['message'])
    else:
        print(entry['level'], entry['message'])

driver.save_screenshot('D:/이음/prototype/debug_screenshot.png')
print("Screenshot saved.")
driver.quit()

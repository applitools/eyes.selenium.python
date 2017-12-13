# from selenium import webdriver
from appium import webdriver
from applitools import logger
from applitools.eyes import Eyes
import os


# Appium session configuration.
from applitools.logger import StdoutLogger

desired_capabilities = {'platformName': 'Android',
                        # 'deviceName': 'Samsung Galaxy S5',
                        # 'platformVersion': '4.2',
                        'deviceName': 'Android Emulator',
                        'platformVersion': '6.0',
                        # 'app': os.environ['ANDROID_NOTES_LIST_APP'],
                        # 'app-package': 'com.example.android.notepad',
                        # 'app-activity': '.NotesList',
                        'app': 'http://saucelabs.com/example_files/ContactManager.apk',
                        # 'browserName': 'chrome',
                        'clearSystemFiles': True,
                        'noReset': True,
                        'newCommandTimeout': 300}

# Assuming Appium is running on localhost.
# driver = webdriver.Remote('http://127.0.0.1:4723/wd/hub', desired_capabilities)
# Appium from saucelabs
SAUCE_ACCESS_KEY = os.environ["SAUCE_ACCESS_KEY"]
SAUCE_USERNAME  = os.environ["SAUCE_USERNAME"]
url = "https://{}:{}@ondemand.saucelabs.com:443/wd/hub".format(SAUCE_USERNAME, SAUCE_ACCESS_KEY)
driver = webdriver.Remote(url, desired_capabilities)
driver.orientation = 'LANDSCAPE'
logger.set_logger(StdoutLogger())
eyes = Eyes()
eyes.api_key = os.environ['APPLITOOLS_API_KEY']
try:
    eyes.open(driver, 'Appium', 'Contact manager')
    eyes.check_window('Opening screen')
    eyes.close()
finally:
    driver.quit()
    eyes.abort_if_not_closed()

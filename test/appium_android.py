# from selenium import webdriver
from appium import webdriver
from applitools import logger
from applitools.eyes import Eyes
import os


# Appium session configuration.
from applitools.logger import StdoutLogger

desired_capabilities = {'platformName': 'Android',
                        'platformVersion': '4.2',
                        'deviceName': 'Samsung Galaxy S5',
                        'app': os.environ['ANDROID_NOTES_LIST_APP'],
                        'app-package': 'com.example.android.notepad',
                        'app-activity': '.NotesList',
                        'newCommandTimeout': 300}

# Assuming Appium is running on localhost.
driver = webdriver.Remote('http://127.0.0.1:4723/wd/hub', desired_capabilities)
driver.orientation = 'LANDSCAPE'
logger.set_logger(StdoutLogger())
eyes = Eyes("https://localhost.applitools.com")
eyes.api_key = os.environ['APPLITOOLS_API_KEY']
eyes.baseline_name = "NotesList 1080x1794"
try:
    eyes.open(driver, 'Appium', 'Notes list')
    eyes.check_window('Opening screen')
    eyes.close()
finally:
    driver.quit()
    eyes.abort_if_not_closed()

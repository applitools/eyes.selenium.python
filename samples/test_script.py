from selenium import webdriver
from applitools import logger
from applitools.logger import StdoutLogger
from applitools.eyes import Eyes
from applitools.common import StitchMode

import os
#os.environ['HTTPS_PROXY'] = "http://localhost:8888"

driver = webdriver.Chrome()

eyes = Eyes()
eyes.api_key = os.environ['APPLITOOLS_API_KEY']

logger.set_logger(StdoutLogger())

# Force Eyes to grab a full page screenshot.
eyes.force_full_page_screenshot = True
eyes.stitch_mode = StitchMode.CSS

try:
    driver = eyes.open(driver, "Python app", "applitools", {'width': 800, 'height': 600})
    driver.get('http://www.applitools.com')
    eyes.check_window("Home")

    automated_paragraph = driver.find_element_by_class_name("automated")
    eyes.check_region_by_element(automated_paragraph, "Automated Testing Paragraph")

    eyes.close()
finally:
    driver.quit()
    eyes.abort_if_not_closed()

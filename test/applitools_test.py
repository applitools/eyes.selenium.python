import os
from selenium import webdriver
from applitools import logger
from applitools.eyes import Eyes
from applitools.logger import StdoutLogger

# os.environ['HTTPS_PROXY'] = "http://localhost:8888"

driver = webdriver.Chrome()

logger.set_logger(StdoutLogger())
eyes = Eyes()
eyes.api_key = os.environ['APPLITOOLS_API_KEY']
eyes.force_full_page_screenshot = True
eyes.hide_scrollbars = True

try:
    ## First test
    driver = eyes.open(driver, "Python app", "Github Website", {'width': 800, 'height': 600})
    driver.get('http://www.github.com')
    eyes.check_window("initial")
    results = eyes.close(False)
    print(results)

    ## Second test
    driver = eyes.open(driver, "Python app", "Applitools Website", {'width': 900, 'height': 600})
    driver.get('http://www.applitools.com')
    eyes.check_window("initial")
    results = eyes.close(False)
    print(results)
finally:
    driver.quit()
    eyes.abort_if_not_closed()

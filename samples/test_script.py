import os
from selenium import webdriver
from applitools import logger
from applitools.common import StitchMode
from applitools.eyes import Eyes
from applitools.logger import StdoutLogger

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

    hero = driver.find_element_by_class_name("hero-container")
    eyes.check_region_by_element(hero, "Page Hero")

    eyes.close()
finally:
    driver.quit()
    eyes.abort_if_not_closed()

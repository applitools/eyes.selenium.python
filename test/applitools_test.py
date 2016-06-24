import os
from selenium import webdriver
from applitools import logger
from applitools.eyes import Eyes
from applitools.logger import StdoutLogger

# os.environ['HTTPS_PROXY'] = "http://localhost:8888"

driver = webdriver.Chrome()

logger.set_logger(StdoutLogger())
eyes = Eyes("https://localhost.applitools.com")
eyes.api_key = os.environ['APPLITOOLS_API_KEY']
eyes.force_full_page_screenshot = True
eyes.save_new_tests = False

try:
    ## First test
    driver = eyes.open(driver, "Python app", "Python binary", {'width': 800, 'height': 600})

    driver.get('http://www.applitools.com')
    eyes.check_window("initial")

    ## Second test
    # driver.find_element_by_class_name("input-name").send_keys("my name is what?")
    # eyes.check_window("name input")
    # results = eyes.close(False)
    # print(results)
    #
    # driver = eyes.open(driver, "Python app", "Python binary", {'width': 800, 'height': 600})
    # driver.get('http://www.applitools.com')
    # eyes.check_window("initial")
    results = eyes.close(False)
    print(results)
finally:
    driver.quit()
    eyes.abort_if_not_closed()

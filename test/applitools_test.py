from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from applitools import logger
from applitools.logger import StdoutLogger, FileLogger
from applitools.eyes import Eyes

import os
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

    pricing_element = driver.find_element_by_css_selector("li.pricing a")
    eyes.check_region_by_element(pricing_element, "pricing button")

    driver.find_element_by_css_selector("li.contact-us a").click()
    eyes.check_window("contact us page")

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

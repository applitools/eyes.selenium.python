import uuid
from pytest import fixture, raises
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By

from applitools import logger
from applitools.errors import DiffsFoundError
from applitools.eyes import Eyes, BatchInfo
from applitools.logger import StdoutLogger

# os.environ['HTTPS_PROXY'] = "http://localhost:8888"


@fixture(scope="function", autouse=True, name="eyes")
def setup_eyes(request):
    logger.set_logger(StdoutLogger())
    eyes = Eyes()
    # eyes.force_full_page_screenshot = True
    # eyes.save_new_tests = False
    eyes.hide_scrollbars = True

    def fin():
        eyes.abort_if_not_closed()

    request.addfinalizer(fin)
    return eyes


@fixture(scope="module", autouse=True, name="driver")
def setup_driver(request):
    sauce_username = os.environ['SAUCE_USERNAME']
    sauce_access_key = os.environ['SAUCE_ACCESS_KEY']
    saucelabs_url = "https://{}:{}@ondemand.saucelabs.com:443/wd/hub".format(sauce_username, sauce_access_key)
    desired_cap = {'platform': 'Windows 10', 'browserName': 'chrome'}
    driver = webdriver.Remote(
        command_executor=saucelabs_url,
        desired_capabilities=desired_cap)
    def fin():
        driver.quit()
    request.addfinalizer(fin)
    return driver


def test_session_summary_status_new(eyes, driver):
    # First test
    driver = eyes.open(driver, "Python SDK", "TestResults-New_{}".format(str(uuid.uuid4())), {'width': 800, 'height': 600})
    driver.get('http://applitools.github.io/demo/TestPages/FramesTestPage/')
    eyes.check_window("initial")
    eyes.close()


def test_summary_status_diffsfound(eyes, driver):
    # Second test
    driver = eyes.open(driver, "Python SDK", "TestResults-DiffsFound", {'width': 800, 'height': 600})
    driver.get('http://applitools.github.io/demo/TestPages/FramesTestPage/')
    eyes.check_window("initial")
    with raises(DiffsFoundError):
        eyes.close()


def test_directly_set_viewport_size(eyes, driver):
    required_viewport = {'width': 450, 'height': 300}
    eyes.set_viewport_size(driver, required_viewport)
    driver = eyes.open(driver, "Python SDK", "TestViewPort-DirectlySetViewportt")
    assert required_viewport == eyes.get_viewport_size()
    assert required_viewport == driver.get_viewport_size()


def test_check_region_stitch(eyes, driver):
    eyes.batch = BatchInfo('Python SDK Test')
    eyes.force_full_page_screenshot = True
    driver.get("http://applitools.github.io/demo/TestPages/FramesTestPage/")
    driver = eyes.open(driver, 'Eyes Selenium SDK - Classic API', 'TestCheckRegion_Linux',
                       viewport_size={'width': 800, 'height': 600})
    eyes.check_region_by_selector(By.ID, "overflowing-div", tag="Region", stitch_content=True)
    eyes.close()

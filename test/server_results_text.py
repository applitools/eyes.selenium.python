import uuid
from pytest import fixture, raises
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from applitools import logger
from applitools.errors import DiffsFoundError
from applitools.eyes import Eyes
from applitools.logger import StdoutLogger

# os.environ['HTTPS_PROXY'] = "http://localhost:8888"


@fixture(scope="module", autouse=True, name="eyes")
def setup_eyes(request):
    logger.set_logger(StdoutLogger())
    eyes = Eyes()
    eyes.api_key = os.environ['APPLITOOLS_API_KEY']
    # eyes.force_full_page_screenshot = True
    # eyes.save_new_tests = False
    eyes.hide_scrollbars = True

    def fin():
        eyes.abort_if_not_closed()

    request.addfinalizer(fin)
    return eyes


@fixture(scope="module", autouse=True, name="driver")
def setup_driver(request):
    chrome_options = Options()
    chrome_options.add_argument('disable-infobars')
    chrome_options.add_argument('headless')
    driver = webdriver.Chrome(chrome_options=chrome_options)

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



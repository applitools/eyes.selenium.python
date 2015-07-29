"""
Selenium/web driver related utilities.
"""
import time
from applitools import logger
from applitools.errors import EyesError
from .errors import TestFailedError

_GET_VIEWPORT_HEIGHT_JAVASCRIPT_FOR_NORMAL_BROWSER = 'return window.innerHeight'
_GET_VIEWPORT_WIDTH_JAVASCRIPT_FOR_NORMAL_BROWSER = 'return window.innerWidth'

_DOCUMENT_CLEAR_SCROLL_BARS_JAVASCRIPT = "var doc = document.documentElement; " + \
                                         "var previousOverflow = doc.style.overflow;"
_DOCUMENT_RESET_SCROLL_BARS_JAVASCRIPT = "doc.style.overflow = previousOverflow;"

_DOCUMENT_RETURN_JAVASCRIPT = "return __applitools_result;"

_GET_VIEWPORT_WIDTH_JAVASCRIPT_FOR_BAD_BROWSERS = _DOCUMENT_CLEAR_SCROLL_BARS_JAVASCRIPT + \
                                                  "var __applitools_result = doc.clientWidth;" + \
                                                  _DOCUMENT_RESET_SCROLL_BARS_JAVASCRIPT + \
                                                  _DOCUMENT_RETURN_JAVASCRIPT

_GET_VIEWPORT_HEIGHT_JAVASCRIPT_FOR_BAD_BROWSERS = _DOCUMENT_CLEAR_SCROLL_BARS_JAVASCRIPT + \
                                                   "var __applitools_result = doc.clientHeight;" + \
                                                   _DOCUMENT_RESET_SCROLL_BARS_JAVASCRIPT + \
                                                   _DOCUMENT_RETURN_JAVASCRIPT


def extract_viewport_width_no_scrollbar(driver):
    return driver.execute_script("return document.documentElement.clientWidth")


def extract_viewport_height_no_scrollbar(driver):
    return driver.execute_script("return document.documentElement.clientHeight")


def extract_viewport_size_no_scrollbars(driver):
    return {'width': extract_viewport_width_no_scrollbar(driver),
            'height': extract_viewport_height_no_scrollbar(driver)}


def extract_viewport_width(driver):
    # noinspection PyBroadException
    try:
        width = driver.execute_script(_GET_VIEWPORT_WIDTH_JAVASCRIPT_FOR_NORMAL_BROWSER)
        if width is None:
            width = driver.execute_script(_GET_VIEWPORT_WIDTH_JAVASCRIPT_FOR_BAD_BROWSERS)
    except:
        width = driver.execute_script(_GET_VIEWPORT_WIDTH_JAVASCRIPT_FOR_BAD_BROWSERS)
    return width


def extract_viewport_height(driver):
    # noinspection PyBroadException
    try:
        height = driver.execute_script(_GET_VIEWPORT_HEIGHT_JAVASCRIPT_FOR_NORMAL_BROWSER)
        if height is None:
            height = driver.execute_script(_GET_VIEWPORT_HEIGHT_JAVASCRIPT_FOR_BAD_BROWSERS)
    except:
        height = driver.execute_script(_GET_VIEWPORT_HEIGHT_JAVASCRIPT_FOR_BAD_BROWSERS)
    return height


def get_viewport_size(driver):
    """
    Tries to get the viewport size using Javascript. If fails, gets the entire browser window
    size!
    """
    # noinspection PyBroadException
    try:
        width = extract_viewport_width(driver)
        height = extract_viewport_height(driver)
        return {'width': width, 'height': height}
    except:
        logger.info('Failed to get viewport size. Only window size is available')
        browser_size = driver.get_window_size()
        return {'width': browser_size['width'], 'height': browser_size['height']}


def _verify_size(to_verify, required_size, sleep_time=1, retries=3):
    for retry in range(retries):
        time.sleep(sleep_time)
        current_size = to_verify()
        if current_size['width'] == required_size['width'] \
           and current_size['height'] == required_size['height']:
            return True
    return False


def set_viewport_size(driver, required_size):
    if 'width' not in required_size or 'height' not in required_size:
        raise EyesError('Size must have width & height keys!')

    logger.debug("set_viewport_size({0})".format(required_size))
    starting_size = required_size
    # When setting the viewport size we need to be in the default content frame
    original_frame_chain = driver.get_frame_chain()
    driver.switch_to.default_content()

    driver.set_window_size(required_size['width'], required_size['height'])
    if not _verify_size(driver.get_window_size, starting_size):
        error_message = "Failed to set browser size!"
        logger.info(error_message)
        # Going back to the frame we started at
        driver.switch_to.frames(original_frame_chain)
        raise TestFailedError(error_message)
    current_viewport_size = get_viewport_size(driver)
    logger.debug("set_viewport_size(): initial viewport size: {0}".format(current_viewport_size))
    current_browser_size = driver.get_window_size()
    width_to_set = (2 * current_browser_size['width']) - current_viewport_size['width']
    height_to_set = (2 * current_browser_size['height']) - current_viewport_size['height']
    driver.set_window_size(width_to_set, height_to_set)
    if not _verify_size(lambda: get_viewport_size(driver), required_size):
        current_viewport_size = get_viewport_size(driver)
        logger.debug("set_viewport_size(): viewport size: {0}".format(current_viewport_size))
        logger.debug("set_viewport_size(): attempting one more time...")
        current_browser_size = driver.get_window_size()
        updated_width = current_browser_size['width'] + (required_size['width']
                                                         - current_viewport_size['width'])
        updated_height = current_browser_size['height'] + (required_size['height']
                                                           - current_viewport_size['height'])
        updated_browser_size = {'width': updated_width, 'height': updated_height}
        logger.debug("set_viewport_size(): browser size: {0}".format(current_browser_size))
        logger.debug("set_viewport_size(): required browser size: {0}".format(updated_browser_size))
        driver.set_window_size(updated_width, updated_height)
        if not _verify_size(lambda: get_viewport_size(driver), required_size):
            current_viewport_size = get_viewport_size(driver)
            logger.debug("set_viewport_size(): viewport size: {0}".format(current_viewport_size))
            error_message = "Failed to set viewport size."
            logger.info(error_message)
            # Going back to the frame we started at
            driver.switch_to.frames(original_frame_chain)
            raise TestFailedError(error_message)
    # Going back to the frame we started at
    driver.switch_to.frames(original_frame_chain)

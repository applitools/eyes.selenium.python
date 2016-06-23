"""
Selenium/web driver related utilities.
"""
import time

from applitools import logger
from applitools.errors import EyesError

_JS_GET_VIEWPORT_SIZE = "var height = undefined;" \
                        "var width = undefined;" \
                        "  if (window.innerHeight) {height = window.innerHeight;}" \
                        "  else if (document.documentElement " \
                        "&& document.documentElement.clientHeight) " \
                        "{height = document.documentElement.clientHeight;}" \
                        "  else { var b = document.getElementsByTagName('body')[0]; " \
                        "if (b.clientHeight) {height = b.clientHeight;}" \
                        "};" \
                        " if (window.innerWidth) {width = window.innerWidth;}" \
                        " else if (document.documentElement " \
                        "&& document.documentElement.clientWidth) " \
                        "{width = document.documentElement.clientWidth;}" \
                        " else { var b = document.getElementsByTagName('body')[0]; " \
                        "if (b.clientWidth) {" \
                        "width = b.clientWidth;}" \
                        "};" \
                        "return [width, height];"


def get_viewport_size(driver):
    """
    Tries to get the viewport size using Javascript. If fails, gets the entire browser window
    size!
    :param driver: The webdriver to use for getting the viewport size.
    """
    # noinspection PyBroadException
    try:
        width, height = driver.execute_script(_JS_GET_VIEWPORT_SIZE)
    except:
        logger.info('Failed to get viewport size. Only window size is available')
        browser_size = driver.get_window_size()
        width, height = browser_size['width'], browser_size['height']
    return {'width': width, 'height': height}


def _verify_size(verification_func, required_size, sleep_time=1, retries=3):
    for retry in range(retries):
        time.sleep(sleep_time)
        current_size = verification_func()
        if current_size['width'] == required_size['width'] \
                and current_size['height'] == required_size['height']:
            return True
    return False


def set_viewport_size(driver, required_size):
    if 'width' not in required_size or 'height' not in required_size:
        raise EyesError('Size must have width & height keys!')
    logger.debug("set_viewport_size({0})".format(required_size))
    # We move the window to (0,0) to have the best chance to be able to set the viewport size as requested.
    driver.set_window_position(0, 0)
    starting_size = required_size
    driver.set_window_size(required_size['width'], required_size['height'])
    if not _verify_size(driver.get_window_size, starting_size):
        raise EyesError('Failed to set browser size!')
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
        updated_width = current_browser_size['width'] + (required_size['width'] - current_viewport_size['width'])
        updated_height = current_browser_size['height'] + (required_size['height'] - current_viewport_size['height'])
        updated_browser_size = {'width': updated_width, 'height': updated_height}
        logger.debug("set_viewport_size(): browser size: {0}".format(current_browser_size))
        logger.debug("set_viewport_size(): required browser size: {0}".format(updated_browser_size))
        driver.set_window_size(updated_width, updated_height)
        if not _verify_size(lambda: get_viewport_size(driver), required_size):
            current_viewport_size = get_viewport_size(driver)
            logger.debug("set_viewport_size(): viewport size: {0}".format(current_viewport_size))
            raise EyesError('Failed to set viewport size.')

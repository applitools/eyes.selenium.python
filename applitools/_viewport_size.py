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
        return {'width': width, 'height': height}
    except:
        logger.info('Failed to get viewport size. Only window size is available')
        return driver.get_window_size()


def set_viewport_size(driver, required_size):
    """
    Tries to set the viewport size.

    :param driver: The webdriver to use for getting the viewport size.
    :param required_size: The size that the viewport size should be set to.
    :return: None.
    :raise EyesError: If the viewport size or browser couldn't be set.
    """
    _BROWSER_SIZE_CALCULATION_RETRIES = 2
    _BROWSER_SET_SIZE_RETRIES = 3
    _BROWSER_STABILIZATION_WAIT = 1  # Seconds
    logger.debug("set_viewport_size({0})".format(required_size))
    if 'width' not in required_size or 'height' not in required_size:
        raise EyesError('Size must have width & height keys!')

    actual_viewport_size = get_viewport_size(driver)
    logger.debug("Current viewport size: {}".format(actual_viewport_size))
    if actual_viewport_size == required_size:
        return
    # If the browser was initially maximized, we might need to repeat the process (border size for maximized browser is
    # sometimes different than non-maximized).
    for _ in range(_BROWSER_SIZE_CALCULATION_RETRIES):
        # We move the window to (0,0) to have the best chance to be able to set the viewport size as requested.
        driver.set_window_position(0, 0)
        browser_size = driver.get_window_size()
        logger.debug("Current browser size: {}".format(browser_size))
        required_browser_size = {
            'width': browser_size['width'] + (required_size['width'] - actual_viewport_size['width']),
            'height': browser_size['height'] + (required_size['height'] - actual_viewport_size['height'])
            }
        logger.debug("Trying to set browser size to: {}".format(required_browser_size))
        for retry in range(_BROWSER_SET_SIZE_RETRIES):
            driver.set_window_size(required_browser_size['width'], required_browser_size['height'])
            time.sleep(_BROWSER_STABILIZATION_WAIT)
            browser_size = driver.get_window_size()
            if (browser_size['width'] == required_browser_size['width'] and
                   browser_size['height'] == required_browser_size['height']):
                break
            logger.debug("Current browser size: {}".format(browser_size))
        else:
            raise EyesError('Failed to set browser size!')

        actual_viewport_size = get_viewport_size(driver)
        logger.debug("Current viewport size: {}".format(actual_viewport_size))
        if actual_viewport_size == required_size:
            return
    else:
        raise EyesError('Failed to set the viewport size.')

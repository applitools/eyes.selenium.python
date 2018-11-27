from collections import namedtuple
from itertools import chain

from selenium.webdriver import FirefoxOptions
from selenium.webdriver import ChromeOptions


class Platform(namedtuple('Platform', 'name version browsers extra')):
    def platform_capabilities(self):
        """
        Get capabilities for mobile platform
        :rtype: collections.Iterable[dict]
        """
        if not self.is_appium_based:
            return

        caps = {'platformName': self.name, 'platformVersion': self.version}
        if isinstance(self.extra, dict):
            caps.update(self.extra)
        return caps

    def browsers_capabilities(self, headless=False):
        """
        Get all browsers capabilities for the platform
        :rtype: collections.Iterable[dict]
        """
        for browser_name, _ in self.browsers:
            yield self.get_browser_capabilities(browser_name, headless)

    def get_browser_capabilities(self, browser_name, headless=False):
        """
        Get browser capabilities for specific browser with included options inside

        :param browser_name: browser name in lowercase
        :type browser_name: str
        :param headless: run browser without gui
        :type headless: bool
        :return: capabilities for specific browser
        :rtype: dict
        """
        if self.is_appium_based:
            return

        options = None
        if 'firefox' == browser_name:
            options = FirefoxOptions()
        elif 'chrome' == browser_name:
            options = ChromeOptions()
            options.add_argument('disable-infobars')
        if options and headless:
            options.headless = True

        # huck for preventing overwriting 'platform' value in desired_capabilities by chrome options
        browser_caps = options.to_capabilities() if options else {}
        browser_name, browser_version = [b for b in self.browsers if browser_name.lower() == b[0].lower()][0]
        browser_caps.update({'browserName': browser_name,
                             'version':     browser_version,
                             'platform':    self.full_name})
        if isinstance(self.extra, dict):
            browser_caps.update(self.extra)
        return browser_caps

    @property
    def is_appium_based(self):
        if self.extra and ('appiumVersion' in self.extra or 'deviceName' in self.extra):
            return True
        return False

    @property
    def full_name(self):
        if self.version:
            return '{} {}'.format(self.name, self.version)
        return self.name


COMMON_BROWSERS = [('chrome', 'latest'), ('firefox', 'latest')]
SUPPORTED_PLATFORMS = [
    Platform(name='Windows', version='10', browsers=COMMON_BROWSERS + [('internet explorer', 'latest'),
                                                                       ('MicrosoftEdge', 'latest')], extra=None),
    Platform(name='Linux', version='', browsers=COMMON_BROWSERS, extra=None),
    Platform(name='macOS', version='10.13', browsers=COMMON_BROWSERS + [('safari', 'latest')], extra=None),

    Platform(name='iPhone', version='11.3', browsers=[], extra={
        "appiumVersion":     "1.9.1",
        "deviceName":        "Iphone Emulator",
        "deviceOrientation": "portrait",
        "browserName":       "Safari",
        "newCommandTimeout": 60 * 5
    }),
    Platform(name='Android', version='6.0', browsers=[], extra={
        "appiumVersion":     "1.9.1",
        "deviceName":        "Android Emulator",
        "deviceOrientation": "portrait",
        "browserName":       "Chrome",
        "newCommandTimeout": 60 * 5
    }),
    Platform(name='Android', version='7.0', browsers=[], extra={
        "appiumVersion":     "1.9.1",
        "deviceName":        "Android Emulator",
        "deviceOrientation": "portrait",
        "browserName":       "Chrome",
        "newCommandTimeout": 60 * 5
    }),
    Platform(name='Android', version='8.0', browsers=[], extra={
        "appiumVersion":     "1.9.1",
        "deviceName":        "Samsung S9+",
        "deviceOrientation": "portrait",
        "browserName":       "Chrome",
        "newCommandTimeout": 60 * 5
    })
]
SUPPORTED_PLATFORMS_DICT = {platform.full_name: platform for platform in SUPPORTED_PLATFORMS}
SUPPORTED_BROWSERS = set(chain(*[platform.browsers for platform in SUPPORTED_PLATFORMS]))

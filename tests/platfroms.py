from collections import namedtuple
from itertools import chain


class Platform(namedtuple('Platform', 'name version browsers extra')):
    def platform_capabilities(self):
        if not self.is_appium_based:
            return

        caps = {'platformName': self.name, 'platformVersion': self.version}
        if isinstance(self.extra, dict):
            caps.update(self.extra)
        return caps

    def browsers_capabilities(self):
        for browser_name, _ in self.browsers:
            yield self.get_browser_capabilities(browser_name)

    def get_browser_capabilities(self, browser_name):
        if self.is_appium_based:
            return
        browser_name, browser_version = [b for b in self.browsers if browser_name.lower() == b[0]][0]
        browser_caps = {'browserName': browser_name, 'version': browser_version, 'platform': self.full_name}
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


COMMON_BROWSERS = [('chrome', '48.0'), ('firefox', '45.0')]
SUPPORTED_PLATFORMS = [
    Platform(name='Windows', version='10', browsers=COMMON_BROWSERS + [('internet explorer', 11)], extra=None),
    Platform(name='Linux', version='', browsers=COMMON_BROWSERS, extra=None),
    Platform(name='macOS', version='10.12', browsers=COMMON_BROWSERS, extra=None),

    Platform(name='iPhone', version='10.0', browsers=[], extra={
        "appiumVersion": "1.7.2",
        "deviceName": "Iphone Emulator",
        "deviceOrientation": "portrait",
        "browserName": "Safari",
    }),
    Platform(name='Android', version='6.0', browsers=[], extra={
        "appiumVersion": "1.7.2",
        "deviceName": "Android Emulator",
        "deviceOrientation": "portrait",
        "browserName": "Browser",
    })
]
SUPPORTED_PLATFORMS_DICT = {platform.full_name: platform for platform in SUPPORTED_PLATFORMS}
SUPPORTED_BROWSERS = set(chain(*[platform.browsers for platform in SUPPORTED_PLATFORMS]))

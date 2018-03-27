from applitools.eyes import Eyes
from selenium import webdriver
import unittest
import os


class Unitest(unittest.TestCase):
    eyes = 0
    driver = 0

    def setUp(self):
        self.eyes = Eyes("https://localhost.applitools.com")
        sauce_url = "http://%s:%s@ondemand.saucelabs.com:80/wd/hub"
        caps = webdriver.DesiredCapabilities.CHROME
        caps['screen-resolution'] = "1280x1024"
        caps['platform'] = "Windows 8"
        sauce_user = os.environ['SAUCELABS_USER']
        sauce_key = os.environ['SAUCELABS_KEY']
        self.driver = webdriver.Remote(
            desired_capabilities=caps,
            command_executor=sauce_url % (sauce_user, sauce_key))

    def tearDown(self):
        self.eyes.abort_if_not_closed()
        self.driver.quit()

    def test(self):
        # Start visual testing with browser viewport set to 1024x768.
        # Make sure to use the returned driver from this point on.
        self.driver = self.eyes.open(
            driver=self.driver, app_name='Saucelabs', test_name='Saucelabs test',
            viewport_size={'width': 1100, 'height': 600})
        self.driver.get('https://saucelabs.com')

        # Visual validation point
        self.eyes.check_window('Main Page')

        menu_items = ['Features', 'Pricing', 'Enterprise', 'Docs']
        for item in menu_items:
            self.driver.find_element_by_xpath("//a[contains(.,'" + item + "')]").click()
            # Visual validation point
            self.eyes.check_window(item)

        # End visual testing. Validate visual correctness.
        self.eyes.close()

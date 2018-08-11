import pytest
from selenium.webdriver.common.by import By

from applitools.geometry import Region
from applitools.common import StitchMode
from applitools.target import Target, IgnoreRegionBySelector, FloatingRegion, FloatingBounds


@pytest.mark.platform('Linux')
def test_quikstart_example(eyes, driver):
    required_viewport = {'width': 450, 'height': 300}
    eyes.set_viewport_size(driver, required_viewport)
    eyes.open(driver=driver, app_name='Hello World!', test_name='My first Selenium Python test!',
              viewport_size={'width': 800, 'height': 600})
    driver.get('https://applitools.com/helloworld')
    # Visual checkpoint #1.
    eyes.check_window('Hello!')

    # Click the 'Click me!' button.
    driver.find_element_by_css_selector('button').click()

    # Visual checkpoint #2.
    eyes.check_window('Click!')
    eyes.check_region(Region(20, 20, 50, 50), "step")


def test_sampe_script(eyes, driver):
    eyes.force_full_page_screenshot = True
    eyes.stitch_mode = StitchMode.CSS

    driver = eyes.open(driver, "Python app", "applitools", {'width': 800, 'height': 600})
    driver.get('http://www.applitools.com')
    eyes.check_window("Home", target=(Target()
                                      .ignore(IgnoreRegionBySelector(By.CLASS_NAME, 'hero-container'))
                                      .floating(FloatingRegion(Region(10, 20, 30, 40), FloatingBounds(10, 0, 20, 10))))
                      )

    hero = driver.find_element_by_class_name("hero-container")
    eyes.check_region_by_element(hero, "Page Hero", target=(Target()
                                                            .ignore(Region(20, 20, 50, 50), Region(40, 40, 10, 20))))

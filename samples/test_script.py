from selenium import webdriver
from selenium.webdriver.common.by import By

from applitools.core import logger, StdoutLogger, Region
from applitools.selenium import StitchMode, Eyes, Target, IgnoreRegionBySelector, FloatingRegion, FloatingBounds

# os.environ['HTTPS_PROXY'] = "http://localhost:9999"

driver = webdriver.Chrome()

eyes = Eyes()

logger.set_logger(StdoutLogger())

# Force Eyes to grab a full page screenshot.
eyes.force_full_page_screenshot = True
eyes.stitch_mode = StitchMode.CSS

try:
    driver = eyes.open(driver, "Python app", "applitools", {'width': 800, 'height': 600})
    driver.get('http://www.applitools.com')
    eyes.check_window("Home", target=(Target()
                                      .ignore(IgnoreRegionBySelector(By.CLASS_NAME, 'hero-container'))
                                      .floating(FloatingRegion(Region(10, 20, 30, 40), FloatingBounds(10, 0, 20, 10))))
                      )

    hero = driver.find_element_by_class_name("hero-container")
    eyes.check_region_by_element(hero, "Page Hero", target=(Target()
                                                            .ignore(Region(20, 20, 50, 50), Region(40, 40, 10, 20)))
                                 )

    eyes.close()
finally:
    driver.quit()
    eyes.abort_if_not_closed()

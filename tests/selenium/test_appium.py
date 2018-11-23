import pytest


@pytest.mark.mobile
@pytest.mark.platform('Android')
@pytest.mark.capabilities(**{"app":              "http://saucelabs.com/example_files/ContactManager.apk",
                             "clearSystemFiles": True,
                             "noReset":          True,
                             "browserName":      '',
                             })
@pytest.mark.eyes(hide_scrollbars=False)
def test_android_native(eyes, driver):
    eyes.open(driver, "Contacts!", "My first Appium Python test!")
    eyes.check_window("Contact list!")
    eyes.close()


@pytest.mark.mobile
@pytest.mark.platform('Android')
@pytest.mark.eyes(hide_scrollbars=False)
def test_final_application_android(eyes, driver):
    driver = eyes.open(driver, "sample2", "titleicon5")
    driver.get("http://applitools.com")
    eyes.check_window("test2")
    btn_element = driver.find_element_by_css_selector('button')
    eyes.check_region_by_element(btn_element, stitch_content=True)
    eyes.close()


@pytest.mark.mobile
@pytest.mark.platform('iPhone')
@pytest.mark.eyes(hide_scrollbars=False)
def test_final_application_ios(eyes, driver):
    driver = eyes.open(driver, "sample", "IOS")
    driver.get("http://applitools.com")
    eyes.check_window()
    btn_element = driver.find_element_by_css_selector('button')
    eyes.check_region_by_element(btn_element, stitch_content=True)
    eyes.close()

import os
from selenium import webdriver
from test.applitools_test import run_test

def create_saucelabs_driver(platform, browsername):
    desired_cap = {
        'platform': platform,
        'browserName': browsername
    }
    if browsername == "chrome":
        desired_cap["version"] = "48.0"
    
    saucelabs_url = os.environ['SAUCELABS_URL']
    driver = webdriver.Remote(
        command_executor=saucelabs_url,
        desired_capabilities=desired_cap)
    return driver

def main():
    platforms = ["Windows 10", "Linux", "macOS 10.12"]
    browsers = ["chrome", "firefox"]

    for platform in platforms:
        for browser in browsers:
            print("Running {} {} test".format(platform, browser))
            driver = create_saucelabs_driver(platform, browser)
            run_test(driver)

    print("Running IE test")
    driver = create_saucelabs_driver("Windows 10", "internet explorer")
    run_test(driver)
    print("Done!")

if __name__ == "__main__":
    main()

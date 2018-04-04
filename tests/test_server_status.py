import uuid

import pytest

from applitools.errors import DiffsFoundError
from applitools.eyes import Eyes
from applitools.target import Target


@pytest.mark.platform('Linux')
def test_session_summary_status_new(eyes, driver):
    driver = eyes.open(driver, "Python SDK", "TestResults-New_{}".format(str(uuid.uuid4())),
                       {'width': 800, 'height': 600})
    driver.get('http://applitools.github.io/demo/TestPages/FramesTestPage/')
    eyes.check_window("initial")
    eyes.close()


@pytest.mark.platform('Linux')
def test_summary_status_diffsfound(eyes, driver):
    driver = eyes.open(driver, "Python SDK", "TestResults-DiffsFound", {'width': 800, 'height': 600})
    driver.get('http://applitools.github.io/demo/TestPages/FramesTestPage/')
    eyes.check_window("initial")
    with pytest.raises(DiffsFoundError):
        eyes.close()


@pytest.mark.platform('Linux')
@pytest.mark.skip("Depending on Fluent API. Not implemented yet")
def test_server_connector(driver):
    eyes = Eyes('https://localhost.applitools.com')
    driver = eyes.open(driver, "Python SDK", "TestDelete", {'width': 800, 'height': 599})
    driver.get("https://applitools.com/helloworld")
    eyes.check("Hello", Target.window())
    results = eyes.close()
    results.delete()
    eyes.abort_if_not_closed()


@pytest.mark.platform('Linux')
def test_directly_set_viewport_size(eyes, driver):
    required_viewport = {'width': 450, 'height': 300}
    eyes.set_viewport_size(driver, required_viewport)
    driver = eyes.open(driver, "Python SDK", "TestViewPort-DirectlySetViewportt")
    assert required_viewport == eyes.get_viewport_size()
    assert required_viewport == driver.get_viewport_size()

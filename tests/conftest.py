import os
import pytest

from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver import ChromeOptions
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.remote_connection import RemoteConnection

from applitools import logger
from applitools import VERSION as applitools_version
from applitools.eyes import Eyes

from tests.platfroms import SUPPORTED_PLATFORMS, SUPPORTED_PLATFORMS_DICT


@pytest.fixture(scope="function")
def eyes(request):
    # TODO: allow to setup logger level through pytest option
    # logger.set_logger(StdoutLogger())
    eyes = Eyes()
    eyes.hide_scrollbars = True

    yield eyes
    eyes.abort_if_not_closed()


@pytest.fixture(scope="function", name="eyes_session")
def eyes_session(request, eyes, driver):
    force_full_page_screenshot = getattr(request, 'param', False)
    eyes.force_full_page_screenshot = force_full_page_screenshot

    test_suite_name = request.cls.test_suite_name
    # convert snake case method name to camel case
    test_name = "{test_name}_{platform_name}".format(test_name=request.function.__name__.title().replace('_', ''),
                                                     platform_name=driver.capabilities['platform'].replace(' ', '_'))
    if force_full_page_screenshot:
        test_suite_name += ' - ForceFPS'
        test_name += '_FPS'
    driver = eyes.open(driver, test_suite_name, test_name,
                       viewport_size={'width': 800, 'height': 600})
    driver.get(request.cls.tested_page_url)

    # TODO: implement eyes.setDebugScreenshotsPrefix("Java_" + testName + "_");

    request.cls.eyes = eyes
    request.cls.driver = driver

    yield
    results = eyes.close()
    print(results)


def pytest_addoption(parser):
    parser.addoption("--platform", action="store")
    parser.addoption("--browser", action="store")


def _get_capabilities(platform_name='Linux', browser_name=None):
    platform = SUPPORTED_PLATFORMS_DICT[platform_name]
    if platform.is_appium_based:
        capabilities = [platform.platform_capabilities()]
    else:
        if browser_name:
            return [platform.get_browser_capabilities(browser_name)]
        capabilities = list(platform.browsers_capabilities())
    return capabilities


def _setup_env_vars_for_session():
    import uuid
    python_version = os.environ.get('TRAVIS_PYTHON_VERSION', None)
    if not python_version:
        import platform
        python_version = platform.python_version()
    os.environ['APPLITOOLS_BATCH_ID'] = os.environ.get('APPLITOOLS_BATCH_ID', str(uuid.uuid4()))
    os.environ['APPLITOOLS_BATCH_NAME'] = 'Python {} | SDK {} Tests'.format(python_version, applitools_version)


def pytest_generate_tests(metafunc):
    platform_name = metafunc.config.getoption('platform')
    browser_name = metafunc.config.getoption('browser')

    _setup_env_vars_for_session()

    if platform_name or browser_name:
        desired_caps = _get_capabilities(platform_name, browser_name)
    else:
        desired_caps = []
        for platform in SUPPORTED_PLATFORMS:
            if platform.is_appium_based:
                desired_caps.append(platform.platform_capabilities())
            else:
                desired_caps.extend(list(platform.browsers_capabilities()))

    # update with capabilities from test function mark.capabilities fixture
    if hasattr(metafunc, 'function'):
        func_capabilities = getattr(metafunc.function, 'capabilities', {})
        if func_capabilities:
            for caps in desired_caps:
                caps.update(func_capabilities.kwargs)

    if 'driver' in metafunc.fixturenames:
        metafunc.parametrize('browser_config',
                             desired_caps,
                             ids=_generate_param_ids('browser_config', desired_caps),
                             scope='function')


def _generate_param_ids(name, values):
    return [("<%s:%s>" % (name, value)).replace('.', '_') for value in values]


@pytest.yield_fixture(scope='function')
def driver(request, browser_config):
    options = None
    browser_name = browser_config.get('browserName').lower()
    platform_name = browser_config.get('platform')
    if 'firefox' == browser_name:
        options = FirefoxOptions()
    elif 'chrome' == browser_name:
        options = ChromeOptions()
        options.add_argument('disable-infobars')

    test_name = request.node.name
    build_tag = os.environ.get('BUILD_TAG', None)
    tunnel_id = os.environ.get('TUNNEL_IDENTIFIER', None)
    username = os.environ.get('SAUCE_USERNAME', None)
    access_key = os.environ.get('SAUCE_ACCESS_KEY', None)

    selenium_url = os.environ.get('SELENIUM_SERVER_URL', 'http://127.0.0.1:4444/wd/hub')
    if 'ondemand.saucelabs.com' in selenium_url:
        selenium_url = "https://%s:%s@ondemand.saucelabs.com:443/wd/hub" % (username, access_key)
        if options:
            options.set_headless()

    # huck for preventing overwriting 'platform' value in desired_capabilities by browser options
    desired_caps = options.to_capabilities() if options else {}
    desired_caps.update(browser_config)

    desired_caps['build'] = build_tag
    desired_caps['tunnelIdentifier'] = tunnel_id
    desired_caps['name'] = test_name

    executor = RemoteConnection(selenium_url, resolve_ip=False)
    browser = webdriver.Remote(
        command_executor=executor,
        desired_capabilities=desired_caps,
    )

    if browser is None:
        raise WebDriverException("Never created!")

    yield browser

    # report results
    try:
        browser.execute_script("sauce:job-result=%s" % str(not request.node.rep_call.failed).lower())
        browser.quit()
    except WebDriverException:
        # we can ignore the exceptions of WebDriverException type -> We're done with tests.
        logger.info('Warning: The driver failed to quit properly. Check test and server side logs.')


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # this sets the result as a test attribute for SauceLabs reporting.
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set an report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"
    setattr(item, "rep_" + rep.when, rep)

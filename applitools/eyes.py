from __future__ import absolute_import

import os
import typing as tp
import uuid
import abc

from datetime import datetime

from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

# noinspection PyProtectedMember
from . import VERSION, _viewport_size, logger
from ._agent_connector import AgentConnector
from ._match_window_task import MatchWindowTask
from ._triggers import MouseTrigger, TextTrigger
from ._webdriver import EyesFrame, EyesWebDriver, EyesScreenshot, EyesWebElement
from .common import StitchMode
from .errors import DiffsFoundError, EyesError, NewTestError, TestFailedError
from .geometry import Region
from .test_results import TestResults, TestResultsStatus
from .utils import general_utils
from .utils.compat import ABC

if tp.TYPE_CHECKING:
    from ._webdriver import EyesScreenshot
    from .target import Target
    from .utils._custom_types import (RunningSession, ViewPort, UserInputs, MatchResult, AppEnvironment,
                                      SessionStartInfo, AnyWebDriver, FrameReference, AnyWebElement)


class FailureReports(object):
    """
    Failures are either reported immediately when they are detected, or when the test is closed.
    """
    IMMEDIATE = "Immediate"
    ON_CLOSE = "OnClose"


class MatchLevel(object):
    """
    The extent in which two images match (or are expected to match).
    """
    NONE = "None"
    LEGACY_LAYOUT = "Layout1"
    LAYOUT = "Layout2"
    LAYOUT2 = "Layout2"
    CONTENT = "Content"
    STRICT = "Strict"
    EXACT = "Exact"


class ScreenshotType(object):
    ENTIRE_ELEMENT_SCREENSHOT = 'EntireElementScreenshot'
    FULLPAGE_SCREENSHOT = "FullPageScreenshot"
    VIEWPORT_SCREENSHOT = "ViewportScreenshot"


class ExactMatchSettings(object):
    """
    Encapsulates settings for the "Exact" match level.
    """

    def __init__(self, min_diff_intensity=0, min_diff_width=0, min_diff_height=0, match_threshold=0.0):
        # type: (int, int, int, float) -> None
        """
        Ctor.

        :param min_diff_intensity: Minimal non-ignorable pixel intensity difference.
        :param min_diff_width: Minimal non-ignorable diff region width.
        :param min_diff_height: Minimal non-ignorable diff region height.
        :param match_threshold: The ratio of differing pixels above which images are considered mismatching.
        """
        self.min_diff_intensity = min_diff_intensity
        self.min_diff_width = min_diff_width
        self.min_diff_height = min_diff_height
        self.match_threshold = match_threshold

    def __getstate__(self):
        return dict(minDiffIntensity=self.min_diff_intensity,
                    minDiffWidth=self.min_diff_width,
                    minDiffHeight=self.min_diff_height,
                    matchThreshold=self.match_threshold)

    # This is required in order for jsonpickle to work on this object.
    # noinspection PyMethodMayBeStatic
    def __setstate__(self, state):
        raise EyesError('Cannot create ExactMatchSettings instance from dict!')

    def __str__(self):
        return "[min diff intensity: %d, min diff width: %d, min diff height: %d, match threshold: %f]" % (
            self.min_diff_intensity, self.min_diff_width, self.min_diff_height, self.match_threshold)


class ImageMatchSettings(object):
    """
    Encapsulates match settings for the a session.
    """

    def __init__(self, match_level=MatchLevel.STRICT, exact_settings=None):
        # type: (tp.Text, tp.Optional[ExactMatchSettings]) -> None
        """
        :param match_level: The "strictness" level of the match.
        :param exact_settings: Parameter for fine tuning the match when "Exact" match level is used.
        """
        self.match_level = match_level
        self.exact_settings = exact_settings

    def __getstate__(self):
        return dict(matchLevel=self.match_level, exact=self.exact_settings)

    # This is required in order for jsonpickle to work on this object.
    # noinspection PyMethodMayBeStatic
    def __setstate__(self, state):
        raise EyesError('Cannot create ImageMatchSettings instance from dict!')

    def __str__(self):
        return "[Match level: %s, Exact match settings: %s]" % (self.match_level, self.exact_settings)


class BatchInfo(object):
    """
    A batch of tests.
    """

    def __init__(self, name=None, started_at=None):
        # type: (tp.Optional[tp.Text], tp.Optional[datetime]) -> None
        if started_at is None:
            started_at = datetime.now(general_utils.UTC)

        self.name = name if name else os.environ.get('APPLITOOLS_BATCH_NAME', None)
        self.started_at = started_at
        self.id_ = os.environ.get('APPLITOOLS_BATCH_ID', str(uuid.uuid4()))

    def __getstate__(self):
        return dict(name=self.name, startedAt=self.started_at.isoformat(), id=self.id_)

    # Required is required in order for jsonpickle to work on this object.
    # noinspection PyMethodMayBeStatic
    def __setstate__(self, state):
        raise EyesError('Cannot create BatchInfo instance from dict!')

    def __str__(self):
        return "%s - %s - %s" % (self.name, self.started_at, self.id_)


class EyesBase(ABC):
    _DEFAULT_MATCH_TIMEOUT = 2000  # Milliseconds
    _DEFAULT_WAIT_BEFORE_SCREENSHOTS = 100  # ms
    BASE_AGENT_ID = "eyes.selenium.python/%s" % VERSION
    DEFAULT_EYES_SERVER = 'https://eyessdk.applitools.com'

    def __init__(self, server_url=DEFAULT_EYES_SERVER):
        # type: (tp.Text) -> None
        """
        Creates a new (possibly disabled) Eyes instance that interacts with the Eyes server.

        :param server_url: The URL of the Eyes server
        """
        self._agent_connector = AgentConnector(server_url)  # type: AgentConnector
        self._should_get_title = False  # type: bool
        self._is_open = False  # type: bool
        self._app_name = None  # type: tp.Optional[tp.Text]
        self._running_session = None  # type: tp.Optional[RunningSession]
        self._match_timeout = EyesBase._DEFAULT_MATCH_TIMEOUT  # type: int
        self._stitch_mode = StitchMode.Scroll  # type: tp.Text
        self._last_screenshot = None  # type: tp.Optional[EyesScreenshot]
        self._should_match_once_on_timeout = False  # type: bool
        self._start_info = None  # type: tp.Optional[SessionStartInfo]
        self._test_name = None  # type: tp.Optional[tp.Text]
        self._user_inputs = []  # type: UserInputs
        self._region_to_check = None

        # key-value pairs to be associated with the test. Can be used for filtering later.
        self._properties = []  # type: tp.List

        # Disables Applitools Eyes and uses the webdriver directly.
        self.is_disabled = False  # type: bool

        # An optional string identifying the current library using the SDK.
        self.agent_id = None  # type: tp.Optional[tp.Text]

        # Should the test report mismatches immediately or when it is finished. See FailureReports.
        self.failure_reports = FailureReports.ON_CLOSE  # type: tp.Text

        # The default match settings for the session. See ImageMatchSettings.
        self.default_match_settings = ImageMatchSettings()  # type: ImageMatchSettings

        # The batch to which the tests belong to. See BatchInfo. None means no batch.
        self.batch = None  # type: tp.Optional[BatchInfo]

        # A string identifying the OS running the AUT. Use this to override Eyes automatic inference.
        self.host_os = None  # type: tp.Optional[tp.Text]

        # A string identifying the app running the AUT. Use this to override Eyes automatic inference.
        self.host_app = None  # type: tp.Optional[tp.Text]

        # A string that, if specified, determines the baseline to compare with and disables automatic baseline
        # inference.
        self.baseline_name = None  # type: tp.Optional[tp.Text]

        # A boolean denoting whether new tests should be automatically accepted.
        self.save_new_tests = True  # type: bool

        # Whether failed tests should be automatically saved with all new output accepted.
        self.save_failed_tests = False  # type: bool

        # A string identifying the branch in which tests are run.
        self.branch_name = None  # type: tp.Optional[tp.Text]

        # A string identifying the parent branch of the branch set by "branch_name".
        self.parent_branch_name = None  # type: tp.Optional[tp.Text]

        # If true, Eyes will treat new tests the same as failed tests.
        self.fail_on_new_test = False  # type: bool

        # The number of milliseconds to wait before each time a screenshot is taken.
        self.wait_before_screenshots = Eyes._DEFAULT_WAIT_BEFORE_SCREENSHOTS  # type: int

    @abc.abstractmethod
    def get_title(self):
        # type: () -> tp.Text
        """
        Returns the title of the window of the AUT, or empty string if the title is not available.
        """

    @abc.abstractmethod
    def get_screenshot(self):
        pass

    @abc.abstractmethod
    def get_viewport_size(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def set_viewport_size(driver, viewport_size):
        pass

    @abc.abstractmethod
    def _assign_viewport_size(self):
        # type: () -> None
        """
        Assign the viewport size we need to be in the default content frame.
        """

    @abc.abstractmethod
    def _get_environment(self):
        # type: () -> AppEnvironment
        """
        Application environment is the environment (e.g., the host OS) which runs the application under test.

        :return: The current application environment.
        """

    @abc.abstractmethod
    def _get_inferred_environment(self):
        pass

    @property
    def seconds_to_wait_screenshot(self):
        return self.wait_before_screenshots / 1000.0

    @property
    def match_level(self):
        # type: () -> tp.Text
        """
        Gets the default match level for the entire session. See ImageMatchSettings.
        """
        return self.default_match_settings.match_level

    @match_level.setter
    def match_level(self, match_level):
        # type: (tp.Text) -> None
        """
        Sets the default match level for the entire session. See ImageMatchSettings.

        :param match_level: The match level to set. Should be one of the values defined by MatchLevel
        """
        self.default_match_settings.match_level = match_level

    @property
    def stitch_mode(self):
        # type: () -> tp.Text
        """
        Gets the stitch mode.

        :return: The stitch mode.
        """
        return self._stitch_mode

    @stitch_mode.setter
    def stitch_mode(self, stitch_mode):
        # type: (tp.Text) -> None
        """
        Sets the stitch property - default is by scrolling.

        :param stitch_mode: The stitch mode to set - either scrolling or css.
        """
        self._stitch_mode = stitch_mode
        if stitch_mode == StitchMode.CSS:
            self.hide_scrollbars = True

    @property
    def match_timeout(self):
        # type: () -> int
        """
        Gets the default timeout for check_XXXX operations. (milliseconds)

        :return: The match timeout (milliseconds)
        """
        return self._match_timeout

    @match_timeout.setter
    def match_timeout(self, match_timeout):
        # type: (int) -> None
        """
        Sets the default timeout for check_XXXX operations. (milliseconds)
        """
        if 0 < match_timeout < MatchWindowTask.MINIMUM_MATCH_TIMEOUT:
            raise ValueError("Match timeout must be at least 60ms.")
        self._match_timeout = match_timeout

    @property
    def api_key(self):
        # type: () -> tp.Text
        """
        Gets the Api key used for authenticating the user with Eyes.

        :return: The Api key used for authenticating the user with Eyes.
        """
        return self._agent_connector.api_key

    @api_key.setter
    def api_key(self, api_key):
        # type: (tp.Text) -> None
        """
        Sets the api key used for authenticating the user with Eyes.

        :param api_key: The api key used for authenticating the user with Eyes.
        """
        self._agent_connector.api_key = api_key  # type: ignore

    @property
    def server_url(self):
        # type: () -> tp.Text
        """
        Gets the URL of the Eyes server.

        :return: The URL of the Eyes server, or None to use the default server.
        """
        return self._agent_connector.server_url

    @server_url.setter
    def server_url(self, server_url):
        # type: (tp.Text) -> None
        """
        Sets the URL of the Eyes server.

        :param server_url: The URL of the Eyes server, or None to use the default server.
        :return: None
        """
        if server_url is None:
            self._agent_connector.server_url = Eyes.DEFAULT_EYES_SERVER
        else:
            self._agent_connector.server_url = server_url

    @property
    def _full_agent_id(self):
        # type: () -> tp.Text
        """
        Gets the agent id, which identifies the current library using the SDK.

        :return: The agent id.
        """
        if self.agent_id is None:
            return self.BASE_AGENT_ID
        return "%s [%s]" % (self.agent_id, self.BASE_AGENT_ID)

    def add_property(self, name, value):
        # type: (tp.Text, tp.Text) -> None
        """
        Associates a key/value pair with the test. This can be used later for filtering.
        :param name: (string) The property name.
        :param value: (string) The property value
        """
        self._properties.append({'name': name, 'value': value})

    def is_open(self):
        # type: () -> bool
        """
        Returns whether the session is currently running.
        """
        return self._is_open

    def close(self, raise_ex=True):
        # type: (bool) -> tp.Optional[TestResults]
        """
        Ends the test.

        :param raise_ex: If true, an exception will be raised for failed/new tests.
        :return: The test results.
        """
        if self.is_disabled:
            logger.debug('close(): ignored (disabled)')
            return None
        try:
            logger.debug('close({})'.format(raise_ex))
            if not self._is_open:
                raise ValueError("Eyes not open")

            self._is_open = False

            self._reset_last_screenshot()

            # If there's no running session, we simply return the default test results.
            if not self._running_session:
                logger.debug('close(): Server session was not started')
                logger.info('close(): --- Empty test ended.')
                return TestResults()

            is_new_session = self._running_session['is_new_session']
            results_url = self._running_session['session_url']

            logger.info("close(): Ending server session...")
            should_save = (is_new_session and self.save_new_tests) or \
                          ((not is_new_session) and self.save_failed_tests)
            logger.debug("close(): automatically save session? %s" % should_save)
            results = self._agent_connector.stop_session(self._running_session, False, should_save)
            results.is_new = is_new_session
            results.url = results_url
            logger.info("close(): %s" % results)

            if results.status == TestResultsStatus.Unresolved:
                if results.is_new:
                    instructions = "Please approve the new baseline at " + results_url
                    logger.info("--- New test ended. " + instructions)
                    if raise_ex:
                        message = "'%s' of '%s'. %s" % (self._start_info['scenarioIdOrName'],
                                                        self._start_info['appIdOrName'],
                                                        instructions)
                        raise NewTestError(message, results)
                else:
                    logger.info("--- Failed test ended. See details at {}".format(results_url))
                    if raise_ex:
                        raise DiffsFoundError("Test '{}' of '{}' detected differences! See details at: {}".format(
                            self._start_info['scenarioIdOrName'],
                            self._start_info['appIdOrName'],
                            results_url), results)
            elif results.status == TestResultsStatus.Failed:
                logger.info("--- Failed test ended. See details at {}".format(results_url))
                if raise_ex:
                    raise TestFailedError("Test '{}' of '{}'. See details at: {}".format(
                        self._start_info['scenarioIdOrName'],
                        self._start_info['appIdOrName'],
                        results_url), results)
            # Test passed
            logger.info("--- Test passed. See details at {}".format(results_url))

            return results
        finally:
            self._running_session = None
            logger.close()

    def abort_if_not_closed(self):
        # type: () -> None
        """
        If a test is running, aborts it. Otherwise, does nothing.
        """
        if self.is_disabled:
            logger.debug('abort_if_not_closed(): ignored (disabled)')
            return
        try:
            self._reset_last_screenshot()

            if self._running_session:
                logger.debug('abort_if_not_closed(): Aborting session...')
                try:
                    self._agent_connector.stop_session(self._running_session, True, False)
                    logger.info('--- Test aborted.')
                except EyesError as e:
                    logger.info("Failed to abort server session: %s " % e)
                    pass
                finally:
                    self._running_session = None
        finally:
            logger.close()

    def open(self, driver, app_name, test_name, viewport_size=None):
        # type: (AnyWebDriver, tp.Text, tp.Text, tp.Optional[ViewPort]) -> AnyWebDriver
        """
        Starts a test.

        :param driver: The webdriver to use.
        :param app_name: The name of the application under test.
        :param test_name: The test name.
        :param viewport_size: The client's viewport size (i.e., the visible part of the document's body) or None to
                                allow any viewport size.
        :return: An updated web driver
        :raise EyesError: If the session was already open.
        """
        logger.open_()
        if self.is_disabled:
            logger.debug('open(): ignored (disabled)')
            return driver

        if self.api_key is None:
            try:
                self.api_key = os.environ['APPLITOOLS_API_KEY']
            except KeyError:
                raise EyesError("API key not set! Log in to https://applitools.com to obtain your"
                                " API Key and use 'api_key' to set it.")

        if isinstance(driver, EyesWebDriver):
            # If the driver is an EyesWebDriver (as might be the case when tests are ran
            # consecutively using the same driver object)
            self._driver = driver
        else:
            if not isinstance(driver, RemoteWebDriver):
                logger.info("WARNING: driver is not a RemoteWebDriver (class: {0})".format(driver.__class__))
            self._driver = EyesWebDriver(driver, self, self._stitch_mode)

        logger.info("open(%s, %s, %s, %s)" % (app_name, test_name, viewport_size, self.failure_reports))

        if self.is_open():
            self.abort_if_not_closed()
            raise EyesError('a test is already running')
        self._app_name = app_name
        self._test_name = test_name
        self._viewport_size = viewport_size
        self._is_open = True
        return self._driver

    def _create_start_info(self):
        # type: () -> None
        app_env = self._get_environment()
        self._start_info = {'agentId': self._full_agent_id, 'appIdOrName': self._app_name,
                            'scenarioIdOrName': self._test_name, 'batchInfo': self.batch,
                            'envName': self.baseline_name, 'environment': app_env,
                            'defaultMatchSettings': self.default_match_settings, 'verId': None,
                            'branchName': self.branch_name, 'parentBranchName': self.parent_branch_name,
                            'properties': self._properties}

    def _start_session(self):
        # type: () -> None
        logger.debug("_start_session()")
        self._assign_viewport_size()

        # initialization of Eyes parameters if empty from ENV variables
        if not self.branch_name:
            self.branch_name = os.environ.get('APPLITOOLS_BRANCH', None)
        if not self.baseline_name:
            self.baseline_name = os.environ.get('APPLITOOLS_BASELINE_BRANCH', None)
        if not self.parent_branch_name:
            self.parent_branch_name = os.environ.get('APPLITOOLS_PARENT_BRANCH', None)
        if not self.batch:
            self.batch = BatchInfo()

        self._create_start_info()
        # Actually start the session.
        self._running_session = self._agent_connector.start_session(self._start_info)
        self._should_match_once_on_timeout = self._running_session['is_new_session']

    def _reset_last_screenshot(self):
        # type: () -> None
        self._last_screenshot = None
        self._user_inputs = []  # type: UserInputs


class Eyes(EyesBase):
    """
    Applitools Selenium Eyes API for python.
    """

    @staticmethod
    def set_viewport_size(driver, viewport_size):
        # type: (AnyWebDriver, ViewPort) -> None
        _viewport_size.set_viewport_size(driver, viewport_size)

    def __init__(self, server_url=EyesBase.DEFAULT_EYES_SERVER):
        super(Eyes, self).__init__(server_url)

        self._driver = None  # type: tp.Optional[AnyWebDriver]
        self._match_window_task = None  # type: tp.Optional[MatchWindowTask]
        self._viewport_size = None  # type: tp.Optional[ViewPort]
        self._screenshot_type = None  # type: tp.Optional[ScreenshotType]

        # If true, Eyes will create a full page screenshot (by using stitching) for browsers which only
        # returns the viewport screenshot.
        self.force_full_page_screenshot = False  # type: bool

        # If true, Eyes will remove the scrollbars from the pages before taking the screenshot.
        self.hide_scrollbars = False  # type: bool

    def _obtain_screenshot_type(self, is_element, inside_a_frame, stitch_content, force_fullpage):
        if stitch_content or force_fullpage:
            if not inside_a_frame:
                if ((force_fullpage and not stitch_content) or
                        (stitch_content and not is_element)):
                    return ScreenshotType.FULLPAGE_SCREENSHOT
            if inside_a_frame or stitch_content:
                return ScreenshotType.ENTIRE_ELEMENT_SCREENSHOT
        else:
            if not stitch_content and not force_fullpage:
                return ScreenshotType.VIEWPORT_SCREENSHOT
        return ScreenshotType.VIEWPORT_SCREENSHOT

    def _get_environment(self):
        os = self.host_os
        # If no host OS was set, check for mobile OS.
        if os is None:
            logger.info('No OS set, checking for mobile OS...')
            # Since in Python Appium driver is the same for Android and iOS, we need to use the desired
            # capabilities to figure this out.
            if self._driver.is_mobile_device():
                platform_name = self._driver.platform_name
                logger.info(platform_name + ' detected')
                platform_version = self._driver.platform_version
                if platform_version is not None:
                    # Notice that Python's "split" function's +limit+ is the the maximum splits performed
                    # whereas in Ruby it is the maximum number of elements in the result (which is why they are set
                    # differently).
                    major_version = platform_version.split('.', 1)[0]
                    os = platform_name + ' ' + major_version
                else:
                    os = platform_name
                logger.info("Setting OS: " + os)
            else:
                logger.info('No mobile OS detected.')
        app_env = {'os': os, 'hostingApp': self.host_app,
                   'displaySize': self._viewport_size,
                   'inferred': self._get_inferred_environment()}
        return app_env

    def get_driver(self):
        # type: () -> EyesWebDriver
        """
        Returns the current web driver.
        """
        return self._driver

    def get_viewport_size(self):
        # type: () -> tp.Dict[tp.Text, int]
        """
        Returns the size of the viewport of the application under test (e.g, the browser).
        """
        return self._driver.get_viewport_size()

    def _assign_viewport_size(self):
        # type: () -> None
        """
        Assign the viewport size we need to be in the default content frame.
        """
        original_frame_chain = self._driver.get_frame_chain()
        self._driver.switch_to.default_content()
        try:
            if self._viewport_size:
                logger.debug("Assigning viewport size {0}".format(self._viewport_size))
                self.set_viewport_size(self._driver, self._viewport_size)
            else:
                logger.debug("No viewport size given. Extracting the viewport size from the driver...")
                self._viewport_size = self.get_viewport_size()
                logger.debug("Viewport size {0}".format(self._viewport_size))
        except EyesError:
            raise TestFailedError('Failed to assign viewport size!')
        finally:
            # Going back to the frame we started at
            self._driver.switch_to.frames(original_frame_chain)

    def get_title(self):
        if self._should_get_title:
            # noinspection PyBroadException
            try:
                return self._driver.title
            except Exception:
                self._should_get_title = False
                # Couldn't get title, return empty string.
        return ''

    def _get_inferred_environment(self):
        # type: () -> tp.Text
        try:
            user_agent = self._driver.execute_script('return navigator.userAgent')
        except WebDriverException:
            user_agent = None
        if user_agent:
            return "useragent:%s" % user_agent
        return None

    def _prepare_to_check(self):
        # type: () -> None
        logger.debug("_prepare_to_check()")
        if not self.is_open():
            raise EyesError('Eyes not open!')

        if not self._running_session:
            self._start_session()
            self._match_window_task = MatchWindowTask(self, self._agent_connector,
                                                      self._running_session, self._driver,
                                                      self.match_timeout)

    def _handle_match_result(self, result, tag):
        # type: (MatchResult, tp.Text) -> None
        self._last_screenshot = result['screenshot']
        as_expected = result['as_expected']
        self._user_inputs = []
        if not as_expected:
            self._should_match_once_on_timeout = True
            if self._running_session and not self._running_session['is_new_session']:
                logger.info("Window mismatch %s" % tag)
                if self.failure_reports == FailureReports.IMMEDIATE:
                    raise TestFailedError("Mismatch found in '%s' of '%s'" %
                                          (self._start_info['scenarioIdOrName'],
                                           self._start_info['appIdOrName']))

    def get_screenshot(self):
        if self.hide_scrollbars:
            original_overflow = self._driver.hide_scrollbars()

        if self._screenshot_type == ScreenshotType.ENTIRE_ELEMENT_SCREENSHOT:
            self._last_screenshot = self._entire_element_screenshot()
        elif self._screenshot_type == ScreenshotType.FULLPAGE_SCREENSHOT:
            self._last_screenshot = self._full_page_screenshot()
        elif self._screenshot_type == ScreenshotType.VIEWPORT_SCREENSHOT:
            self._last_screenshot = self._viewport_screenshot()

        if self.hide_scrollbars:
            # noinspection PyUnboundLocalVariable
            self._driver.set_overflow(original_overflow)
        logger.save_screenshot(self._last_screenshot, 'screenshot')
        return self._last_screenshot

    def _entire_element_screenshot(self):
        logger.info('Entire element screenshot requested')
        screenshot = self._driver.get_stitched_screenshot(self._region_to_check,
                                                          self.seconds_to_wait_screenshot)
        logger.save_screenshot(screenshot, 'entire')
        screenshot = EyesScreenshot.create_from_image(screenshot, self._driver)
        # if (isinstance(self._region_to_check, EyesWebElement) or
        #         isinstance(self._region_to_check, WebElement)):
        #     screenshot = screenshot.get_sub_screenshot_by_element(self._region_to_check)
        #     logger.save_screenshot(screenshot, 'cutted-entire')

        return screenshot

    def _full_page_screenshot(self):
        logger.info('Full page screenshot requested')
        screenshot = self._driver.get_full_page_screenshot(self.seconds_to_wait_screenshot)
        return EyesScreenshot.create_from_image(screenshot, self._driver)

    def _viewport_screenshot(self):
        logger.info('Viewport screenshot requested')
        screenshot64 = self._driver.get_screesnhot_as_base64_from_main_frame(self.seconds_to_wait_screenshot)
        return EyesScreenshot.create_from_base64(screenshot64, self._driver).get_viewport_screenshot()

    def check_window(self, tag=None, match_timeout=-1, target=None):
        # type: (tp.Optional[tp.Text], int, tp.Optional[Target]) -> None
        """
        Takes a snapshot from the browser using the web driver and matches it with the expected
        output.

        :param tag: (str) Description of the visual validation checkpoint.
        :param match_timeout: (int) Timeout for the visual validation checkpoint (milliseconds).
        :param target: (Target) The target for the check_window call
        :return: None
        """
        if self.is_disabled:
            logger.info("check_window(%s): ignored (disabled)" % tag)
            return
        logger.info("check_window('%s')" % tag)
        self._screenshot_type = self._obtain_screenshot_type(is_element=False,
                                                             inside_a_frame=bool(self._driver.get_frame_chain()),
                                                             stitch_content=False,
                                                             force_fullpage=self.force_full_page_screenshot)

        self._prepare_to_check()
        result = self._match_window_task.match_window(match_timeout, tag,
                                                      self._user_inputs,
                                                      self.default_match_settings,
                                                      target,
                                                      self._should_match_once_on_timeout)
        self._handle_match_result(result, tag)

    def check_region(self, region, tag=None, match_timeout=-1, target=None, stitch_content=False):
        # type: (Region, tp.Optional[tp.Text], int, tp.Optional[Target], bool) -> None
        """
        Takes a snapshot of the given region from the browser using the web driver and matches it
        with the expected output. If the current context is a frame, the region is offsetted
        relative to the frame.

        :param region: (Region) The region which will be visually validated. The coordinates are
                         relative to the viewport of the current frame.
        :param tag: (str) Description of the visual validation checkpoint.
        :param match_timeout: (int) Timeout for the visual validation checkpoint (milliseconds).
        :param target: (Target) The target for the check_window call
        :return: None
        """

        if self.is_disabled:
            logger.info('check_region(): ignored (disabled)')
            return
        logger.info("check_region([%s], '%s')" % (region, tag))
        if region.is_empty():
            raise EyesError("region cannot be empty!")

        self._screenshot_type = self._obtain_screenshot_type(is_element=False,
                                                             inside_a_frame=bool(self._driver.get_frame_chain()),
                                                             stitch_content=stitch_content,
                                                             force_fullpage=self.force_full_page_screenshot)
        self._region_to_check = region
        self._prepare_to_check()
        result = self._match_window_task.match_window(match_timeout, tag,
                                                      self._user_inputs,
                                                      self.default_match_settings,
                                                      target,
                                                      self._should_match_once_on_timeout)
        self._handle_match_result(result, tag)

    def check_region_by_element(self, element, tag=None, match_timeout=-1, target=None, stitch_content=False):
        # type: (AnyWebElement, tp.Optional[tp.Text], int, tp.Optional[Target], bool) -> None
        """
        Takes a snapshot of the region of the given element from the browser using the web driver
        and matches it with the expected output.

        :param element: (WebElement)  The element which region will be visually validated.
        :param tag: (str) Description of the visual validation checkpoint.
        :param match_timeout: (int) Timeout for the visual validation checkpoint (milliseconds).
        :param target: (Target) The target for the check_window call
        :return: None
        """
        if self.is_disabled:
            logger.info('check_region_by_element(): ignored (disabled)')
            return
        logger.info("check_region_by_element('%s')" % tag)
        self._screenshot_type = self._obtain_screenshot_type(is_element=True,
                                                             inside_a_frame=bool(self._driver.get_frame_chain()),
                                                             stitch_content=stitch_content,
                                                             force_fullpage=self.force_full_page_screenshot)
        self._prepare_to_check()
        self._region_to_check = element
        result = self._match_window_task.match_window(match_timeout, tag,
                                                      self._user_inputs,
                                                      self.default_match_settings,
                                                      target,
                                                      self._should_match_once_on_timeout)

        self._handle_match_result(result, tag)

    def check_region_by_selector(self, by, value, tag=None, match_timeout=-1, target=None, stitch_content=False):
        # type: (tp.Text, tp.Text, tp.Optional[tp.Text], int, tp.Optional[Target], bool) -> None
        """
        Takes a snapshot of the region of the element found by calling find_element(by, value)
        and matches it with the expected output.

        :param by: (By) The way by which an element to be validated should be found (e.g., By.ID).
        :param value: (str) The value identifying the element using the "by" type.
        :param tag: (str) Description of the visual validation checkpoint.
        :param match_timeout: (int) Timeout for the visual validation checkpoint (milliseconds).
        :param target: (Target) The target for the check_window call
        :return: None
        """
        if self.is_disabled:
            logger.info('check_region_by_selector(): ignored (disabled)')
            return
        logger.debug("calling 'check_region_by_element'...")
        self.check_region_by_element(self._driver.find_element(by, value), tag,
                                     match_timeout, target, stitch_content)

    def check_region_in_frame_by_selector(self, frame_reference,  # type: FrameReference
                                          by,  # type: tp.Text
                                          value,  # type: tp.Text
                                          tag=None,  # type: tp.Optional[tp.Text]
                                          match_timeout=-1,  # type: int
                                          target=None,  # type: tp.Optional[Target]
                                          stitch_content=False  # type: bool
                                          ):
        # type: (...) -> None
        """
        Checks a region within a frame, and returns to the current frame.

        :param frame_reference: (int/str/WebElement) A reference to the frame in which the region should be checked.
        :param by: (By) The way by which an element to be validated should be found (e.g., By.ID).
        :param value: (str) The value identifying the element using the "by" type.
        :param tag: (str) Description of the visual validation checkpoint.
        :param match_timeout: (int) Timeout for the visual validation checkpoint (milliseconds).
        :param target: (Target) The target for the check_window call
        :return: None
        """
        if self.is_disabled:
            logger.info('check_region_in_frame_by_selector(): ignored (disabled)')
            return
        logger.info("check_region_in_frame_by_selector('%s')" % tag)

        # Switching to the relevant frame
        self._driver.switch_to.frame(frame_reference)
        logger.debug("calling 'check_region_by_selector'...")
        self.check_region_by_selector(by, value, tag, match_timeout, target, stitch_content)
        # Switching back to our original frame
        self._driver.switch_to.parent_frame()

    def add_mouse_trigger_by_element(self, action, element):
        # type: (tp.Text, AnyWebElement) -> None
        """
        Adds a mouse trigger.

        :param action: Mouse action (click, double click etc.)
        :param element: The element on which the action was performed.
        """
        if self.is_disabled:
            logger.debug("add_mouse_trigger: Ignoring %s (disabled)" % action)
            return
        # Triggers are activated on the last checked window.
        if self._last_screenshot is None:
            logger.debug("add_mouse_trigger: Ignoring %s (no screenshot)" % action)
            return
        if not EyesFrame.is_same_frame_chain(self._driver.get_frame_chain(),
                                             self._last_screenshot.get_frame_chain()):
            logger.debug("add_mouse_trigger: Ignoring %s (different frame)" % action)
            return
        control = self._last_screenshot.get_intersected_region_by_element(element)
        # Making sure the trigger is within the last screenshot bounds
        if control.is_empty():
            logger.debug("add_mouse_trigger: Ignoring %s (out of bounds)" % action)
            return
        cursor = control.middle_offset
        trigger = MouseTrigger(action, control, cursor)
        self._user_inputs.append(trigger)
        logger.info("add_mouse_trigger: Added %s" % trigger)

    def add_text_trigger_by_element(self, element, text):
        # type: (AnyWebElement, tp.Text) -> None
        """
        Adds a text trigger.

        :param element: The element to which the text was sent.
        :param text: The trigger's text.
        """
        if self.is_disabled:
            logger.debug("add_text_trigger: Ignoring '%s' (disabled)" % text)
            return
        # Triggers are activated on the last checked window.
        if self._last_screenshot is None:
            logger.debug("add_text_trigger: Ignoring '%s' (no screenshot)" % text)
            return
        if not EyesFrame.is_same_frame_chain(self._driver.get_frame_chain(),
                                             self._last_screenshot.get_frame_chain()):
            logger.debug("add_text_trigger: Ignoring %s (different frame)" % text)
            return
        control = self._last_screenshot.get_intersected_region_by_element(element)
        # Making sure the trigger is within the last screenshot bounds
        if control.is_empty():
            logger.debug("add_text_trigger: Ignoring %s (out of bounds)" % text)
            return
        trigger = TextTrigger(control, text)
        self._user_inputs.append(trigger)
        logger.info("add_text_trigger: Added %s" % trigger)

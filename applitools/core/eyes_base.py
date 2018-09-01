from __future__ import absolute_import

import abc
import os
import uuid
import typing as tp
from datetime import datetime

from ..__version__ import __version__
from ..common import StitchMode
from ..utils import general_utils, ABC
from . import logger
from .agent_connector import AgentConnector
from .match_window_task import MatchWindowTask
from .errors import EyesError, NewTestError, DiffsFoundError, TestFailedError
from .test_results import TestResults, TestResultsStatus

if tp.TYPE_CHECKING:
    from ..utils.custom_types import (ViewPort, UserInputs, AppEnvironment,
                                      RunningSession, SessionStartInfo, RegionOrElement)
    from .capture import EyesScreenshotBase

__all__ = ('FailureReports', 'MatchLevel', 'ExactMatchSettings', 'ImageMatchSettings', 'EyesBase')


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
    BASE_AGENT_ID = "eyes.selenium.python/%s" % __version__
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
        self._last_screenshot = None  # type: tp.Optional[EyesScreenshotBase]
        self._should_match_once_on_timeout = False  # type: bool
        self._start_info = None  # type: tp.Optional[SessionStartInfo]
        self._test_name = None  # type: tp.Optional[tp.Text]
        self._user_inputs = []  # type: UserInputs
        self._region_to_check = None  # type: tp.Optional[RegionOrElement]

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
        self.wait_before_screenshots = EyesBase._DEFAULT_WAIT_BEFORE_SCREENSHOTS  # type: int

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
            self._agent_connector.server_url = EyesBase.DEFAULT_EYES_SERVER
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

    def open_base(self, app_name, test_name, viewport_size=None):
        # type: (tp.Text, tp.Text, tp.Optional[ViewPort]) -> None
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
            logger.debug('open_base(): ignored (disabled)')
            return

        if self.api_key is None:
            try:
                self.api_key = os.environ['APPLITOOLS_API_KEY']
            except KeyError:
                raise EyesError("API key not set! Log in to https://applitools.com to obtain your"
                                " API Key and use 'api_key' to set it.")

        logger.info("open(%s, %s, %s, %s)" % (app_name, test_name, viewport_size, self.failure_reports))

        if self.is_open():
            self.abort_if_not_closed()
            raise EyesError('a test is already running')
        self._app_name = app_name
        self._test_name = test_name
        self._viewport_size = viewport_size
        self._is_open = True

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

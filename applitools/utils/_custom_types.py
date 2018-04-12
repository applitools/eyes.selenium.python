import typing as tp
from mypy_extensions import TypedDict

from applitools._triggers import MouseTrigger, TextTrigger

if tp.TYPE_CHECKING:
    from requests.models import Response
    from selenium.webdriver.remote.webdriver import WebDriver
    from applitools.geometry import Region
    from applitools.test_results import TestResults
    from applitools.eyes import Eyes, ImageMatchSettings
    from applitools._webdriver import EyesWebElement, EyesWebDriver, EyesScreenshot
    from applitools._agent_connector import AgentConnector
    from applitools.target import FloatingRegionBySelector, FloatingRegion, FloatingRegionByElement
    from applitools.target import _NopRegionWrapper, IgnoreRegionByElement, IgnoreRegionBySelector

    Num = tp.Union[int, float]
    RunningSession = tp.Dict[tp.Text, tp.Any]
    ViewPort = tp.Dict[tp.Text, int]
    AppOutput = tp.Dict[tp.Text, tp.Any]
    MatchResult = tp.Dict[tp.Text, tp.Any]
    UserInputs = tp.List[tp.Union[MouseTrigger, TextTrigger]]
    AppEnvironment = tp.Dict[tp.Text, tp.Any]
    SessionStartInfo = tp.Dict[tp.Text, tp.Any]
    IgnoreRegion = tp.Union['Region', 'IgnoreRegionByElement', 'IgnoreRegionBySelector', '_NopRegionWrapper']
    FloatingRegionType = tp.Union['FloatingRegion', 'FloatingRegionByElement', 'FloatingRegionBySelector']


    # MatchResult = tp.Dict[tp.Text, tp.Union[bool, EyesScreenshot]]
    # AppEnvironment = tp.Dict[tp.Text, tp.Union[ViewPort, tp.Text, None]]
    # SessionStartInfo = tp.Dict[tp.Text, tp.Union[tp.Text, None, ImageMatchSettings, AppEnvironment]]

import base64
import time

import appium.webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from applitools import logger, _viewport_size
from applitools.errors import EyesError, OutOfBoundsError
from applitools.geometry import Point
from applitools.common import StitchMode
from applitools.utils import _image_utils
from .geometry import Region
from .utils import general_utils


class EyesScreenshot(object):
    @staticmethod
    def create_from_base64(screenshot64, driver):
        """
        Creates an instance from the base64 data.

        :param screenshot64: The base64 representation of the png bytes.
        :param driver: The webdriver for the session.
        """
        return EyesScreenshot(driver, screenshot64=screenshot64)

    @staticmethod
    def create_from_image(screenshot, driver):
        """
        Creates an instance from the base64 data.

        :param screenshot: The screenshot image.
        :param driver: The webdriver for the session.
        """
        return EyesScreenshot(driver, screenshot=screenshot)

    def __init__(self, driver, screenshot=None, screenshot64=None,
                 is_viewport_screenshot=None, frame_location_in_screenshot=None):
        """
        Initializes a Screenshot instance. Either screenshot or screenshot64 must NOT be None.
        Should not be used directly. Use create_from_image/create_from_base64 instead.

        :param driver: EyesWebDriver instance which handles the session from which the screenshot
                    was retrieved.
        :param screenshot: (PngImage) image instance. If screenshot64 is None,
                                    this variable must NOT be none.
        :param screenshot64: The base64 representation of a png image. If screenshot
                                     is None, this variable must NOT be none.
        :param is_viewport_screenshot: Whether the screenshot object represents a
                                                viewport screenshot or a full screenshot.
        :param frame_location_in_screenshot: The location of the frame relative
                                                    to the top,left of the screenshot.
        :raise EyesError: If the screenshots are None.
        """
        self._screenshot64 = screenshot64
        if screenshot:
            self._screenshot = screenshot
        elif screenshot64:
            self._screenshot = _image_utils.png_image_from_bytes(base64.b64decode(screenshot64))
        else:
            raise EyesError("both screenshot and screenshot64 are None!")
        self._driver = driver
        self._viewport_size = driver.get_default_content_viewport_size()

        self._frame_chain = driver.get_frame_chain()
        if self._frame_chain:
            chain_len = len(self._frame_chain)
            self._frame_size = self._frame_chain[chain_len - 1].size
        else:
            try:
                self._frame_size = driver.get_entire_page_size()
            except WebDriverException:
                # For Appium, we can't get the "entire page size", so we use the viewport size.
                self._frame_size = self._viewport_size
        # For native Appium Apps we can't get the scroll position, so we use (0,0)
        try:
            self._scroll_position = driver.get_current_position()
        except WebDriverException:
            self._scroll_position = Point(0, 0)
        if is_viewport_screenshot is None:
            is_viewport_screenshot = self._screenshot.width <= self._viewport_size['width'] \
                and self._screenshot.height <= self._viewport_size['height']
        self._is_viewport_screenshot = is_viewport_screenshot
        if frame_location_in_screenshot is None:
            if self._frame_chain:
                frame_location_in_screenshot = EyesScreenshot \
                    .calc_frame_location_in_screenshot(self._frame_chain, is_viewport_screenshot)
            else:
                # The frame is the default content
                frame_location_in_screenshot = Point(0, 0)
                if self._is_viewport_screenshot:
                    frame_location_in_screenshot.offset(-self._scroll_position.x,
                                                        -self._scroll_position.y)
        self._frame_location_in_screenshot = frame_location_in_screenshot
        self._frame_screenshot_intersect = Region(frame_location_in_screenshot.x,
                                                  frame_location_in_screenshot.y,
                                                  self._frame_size['width'],
                                                  self._frame_size['height'])
        self._frame_screenshot_intersect.intersect(Region(width=self._screenshot.width,
                                                          height=self._screenshot.height))

    @staticmethod
    def calc_frame_location_in_screenshot(frame_chain, is_viewport_screenshot):
        """

        :param frame_chain: List of the frames.
        :param is_viewport_screenshot: Whether the viewport is a screenshot or not.
        :return: The frame location as it would be on the screenshot. Notice that this value
            might actually be OUTSIDE the screenshot (e.g, if this is a viewport screenshot and
            the frame is located outside the viewport). This is not an error. The value can also
            be negative.
        """
        first_frame = frame_chain[0]
        location_in_screenshot = Point(first_frame.location['x'], first_frame.location['y'])
        # We only need to consider the scroll of the default content if the screenshot is a
        # viewport screenshot. If this is a full page screenshot, the frame location will not
        # change anyway.
        if is_viewport_screenshot:
            location_in_screenshot.x -= first_frame.parent_scroll_position.x
            location_in_screenshot.y -= first_frame.parent_scroll_position.y
        # For inner frames we must calculate the scroll
        inner_frames = frame_chain[1:]
        for frame in inner_frames:
            location_in_screenshot.x += frame.location['x'] - frame.parent_scroll_position.x
            location_in_screenshot.y += frame.location['y'] - frame.parent_scroll_position.y
        return location_in_screenshot

    def get_frame_chain(self):
        """
        Returns a copy of the fram chain.

        :return: A copy of the frame chain, as received by the driver when the screenshot was
            created.
        """
        return [frame.clone() for frame in self._frame_chain]

    def get_base64(self):
        """
        Returns a base64 screenshot.

        :return: The base64 representation of the png.
        """
        if not self._screenshot64:
            self._screenshot64 = self._screenshot.get_base64()
        return self._screenshot64

    def get_bytes(self):
        """
        Returns the bytes of the screenshot.

        :return: The bytes representation of the png.
        """
        return self._screenshot.get_bytes()

    def get_location_relative_to_frame_viewport(self, location):
        """
        Gets the relative location from a given location to the viewport.

        :param location: A dict with 'x' and 'y' keys representing the location we want
            to adjust.
        :return: A location (keys are 'x' and 'y') adjusted to the current frame/viewport.
        """
        result = {'x': location['x'], 'y': location['y']}
        if self._frame_chain or self._is_viewport_screenshot:
            result['x'] -= self._scroll_position.x
            result['y'] -= self._scroll_position.y
        return result

    def get_element_region_in_frame_viewport(self, element):
        """
        Gets The element region in the frame.

        :param element: The element to get the region in the frame.
        :return: The element's region in the frame with scroll considered if necessary
        """
        location, size = element.location, element.size

        relative_location = self.get_location_relative_to_frame_viewport(location)

        x, y = relative_location['x'], relative_location['y']
        width, height = size['width'], size['height']
        # We only care about the part of the element which is in the viewport.
        if x < 0:
            diff = -x
            # IMPORTANT the diff is between the original location and the viewport's bounds.
            width -= diff
            x = 0
        if y < 0:
            diff = -y
            height -= diff
            y = 0

        if width <= 0 or height <= 0:
            raise OutOfBoundsError("Element's region is outside the viewport! [(%d, %d) %d x %d]" %
                                   (location['x'], location['y'], size['width'], size['height']))

        return Region(x, y, width, height)

    def get_intersected_region(self, region):
        """
        Gets the intersection of the region with the screenshot image.

        :param region: The region in the frame.
        :return: The part of the region which intersects with
            the screenshot image.
        """
        region_in_screenshot = region.clone()
        region_in_screenshot.left += self._frame_location_in_screenshot.x
        region_in_screenshot.top += self._frame_location_in_screenshot.y
        region_in_screenshot.intersect(self._frame_screenshot_intersect)
        return region_in_screenshot

    def get_intersected_region_by_element(self, element):
        """
        Gets the intersection of the element's region with the screenshot image.

        :param element: The element in the frame.
        :return: The part of the element's region which intersects with
            the screenshot image.
        """
        element_region = self.get_element_region_in_frame_viewport(element)
        return self.get_intersected_region(element_region)

    def get_sub_screenshot_by_region(self, region):
        """
        Gets the region part of the screenshot image.

        :param region: The region in the frame.
        :return: A screenshot object representing the given region part of the image.
        """
        sub_screenshot_region = self.get_intersected_region(region)
        if sub_screenshot_region.is_empty():
            raise OutOfBoundsError("Region {0} is out of bounds!".format(region))
        # If we take a screenshot of a region inside a frame, then the frame's (0,0) is in the
        # negative offset of the region..
        sub_screenshot_frame_location = Point(-region.left, -region.top)

        # FIXME Calculate relative region location? (same as the java version)

        screenshot = self._screenshot.get_subimage(sub_screenshot_region)
        return EyesScreenshot(self._driver, screenshot,
                              is_viewport_screenshot=self._is_viewport_screenshot,
                              frame_location_in_screenshot=sub_screenshot_frame_location)

    def get_sub_screenshot_by_element(self, element):
        """
        Gets the element's region part of the screenshot image.

        :param element: The element in the frame.
        :return: A screenshot object representing the element's region part of the
            image.
        """
        element_region = self.get_element_region_in_frame_viewport(element)
        return self.get_sub_screenshot_by_region(element_region)


class ScrollPositionProvider(object):
    _JS_GET_CURRENT_SCROLL_POSITION = "var doc = document.documentElement; " + \
                                     "var x = window.scrollX || " + \
                                     "((window.pageXOffset || doc.scrollLeft) - (doc.clientLeft || 0));" + \
                                     " var y = window.scrollY || " + \
                                     "((window.pageYOffset || doc.scrollTop) - (doc.clientTop || 0));" + \
                                     "return [x, y]"

    def __init__(self, driver):
        """
        Ctor.

        :param driver: EyesWebDriver instance.
        """
        self.driver = driver
        self.states = []

    def _execute_script(self, script):
        return self.driver.execute_script(script)

    def get_current_position(self):
        """
        Extracts the current scroll position from the browser.

        :return: The scroll position
        """
        try:
            x, y = self._execute_script(self._JS_GET_CURRENT_SCROLL_POSITION)
            if x is None or y is None:
                raise EyesError("Got None as scroll position! ({},{})".format(x, y))
        except WebDriverException:
            raise EyesError("Failed to extract current scroll position!")
        return Point(x, y)

    def set_position(self, point):
        """
        Commands the browser to scroll to a given position using javascript.

        :param point: The point to scroll to.
        """
        scroll_command = "window.scrollTo({0}, {1})".format(point.x, point.y)
        logger.debug(scroll_command)
        self._execute_script(scroll_command)

    def push_state(self):
        """
        Adds the current position to the states list.
        """
        self.states.append(self.get_current_position())

    def pop_state(self):
        """
        Sets the position to be the last position added to the states list.
        """
        self.set_position(self.states.pop())


class CSSTranslatePositionProvider(object):
    _JS_TRANSFORM_KEYS = ["transform", "-webkit-transform" ]

    def __init__(self, driver):
        """
        Ctor.

        :param driver: EyesWebDriver instance.
        """
        self.driver = driver
        self.states = []
        self.current_position = Point(0, 0)

    def _execute_script(self, script):
        return self.driver.execute_script(script)

    def get_current_position(self):
        """
        Extracts the current scroll position from the browser.

        :return: The scroll position.
        """
        return self.current_position.clone()

    def _set_transform(self, transform_list):
        script = ''
        for key, value in transform_list.items():
            script += "document.documentElement.style['{}'] = '{}';".format(key, value)
        self._execute_script(script)

    def _get_current_transform(self):
        script = 'return {'
        for key in self._JS_TRANSFORM_KEYS:
            script += "'{0}': document.documentElement.style['{0}'],".format(key)
        script += ' }'
        return self._execute_script(script)

    def set_position(self, point):
        """
        Commands the browser to scroll to a given position using javascript.

        :param point: The point to set the position at.
        """
        translate_command = "translate(-{}px, -{}px)".format(point.x, point.y)
        logger.debug(translate_command)
        transform_list = dict((key, translate_command) for key in self._JS_TRANSFORM_KEYS)
        self._set_transform(transform_list)
        self.current_position = point.clone()

    def push_state(self):
        """
        Adds the transform to the states list.
        """
        self.states.append(self._get_current_transform())

    def pop_state(self):
        """
        Sets the transform to be the last transform added to the states list.
        """
        self._set_transform(self.states.pop())


def build_position_provider_for(stitch_mode, driver):
    if stitch_mode == StitchMode.Scroll:
        return ScrollPositionProvider(driver)
    elif stitch_mode == StitchMode.CSS:
        return CSSTranslatePositionProvider(driver)
    raise ValueError("Invalid stitch mode: {}".format(stitch_mode))


class EyesWebElement(object):
    """
    A wrapper for selenium web element. This enables eyes to be notified about actions/events for
    this element.
    """
    _METHODS_TO_REPLACE = ['find_element', 'find_elements']

    # Properties require special handling since even testing if they're callable "activates"
    # them, which makes copying them automatically a problem.
    _READONLY_PROPERTIES = ['tag_name', 'text', 'location_once_scrolled_into_view', 'size',
                            'location', 'parent', 'id', 'rect', 'screenshot_as_base64', 'screenshot_as_png',
                            'location_in_view', 'anonymous_children']

    def __init__(self, element, eyes, driver):
        """
        Ctor.

        :param element: The element in the frame.
        :param eyes: The eyes sdk instance.
        :param driver: EyesWebDriver instance.
        """
        self.element = element
        self._eyes = eyes
        self._driver = driver
        # Replacing implementation of the underlying driver with ours. We'll put the original
        # methods back before destruction.
        self._original_methods = {}
        for method_name in self._METHODS_TO_REPLACE:
            self._original_methods[method_name] = getattr(element, method_name)
            setattr(element, method_name, getattr(self, method_name))

        # Copies the web element's interface
        general_utils.create_proxy_interface(self, element, self._READONLY_PROPERTIES)
        # Setting properties
        for attr in self._READONLY_PROPERTIES:
            setattr(self.__class__, attr, general_utils.create_proxy_property(attr, 'element'))

    @property
    def bounds(self):
        # noinspection PyUnresolvedReferences
        location = self.location
        left, top = location['x'], location['y']
        width = height = 0  # Default

        # noinspection PyBroadException
        try:
            size = self.element.size
            width, height = size['width'], size['height']
        except:
            # Not implemented on all platforms.
            pass
        if left < 0:
            left, width = 0, max(0, width + left)
        if top < 0:
            top, height = 0, max(0, height + top)
        return Region(left, top, width, height)

    def find_element(self, by=By.ID, value=None):
        """
        Returns a WebElement denoted by "By".

        :param by: By which option to search for (default is by ID).
        :param value: The value to search for.
        :return: WebElement denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        result = self._original_methods['find_element'](by, value)
        # Wrap the element.
        if result:
            result = EyesWebElement(result, self._eyes, self._driver)
        return result

    def find_elements(self, by=By.ID, value=None):
        """
        Returns a list of web elements denoted by "By".

        :param by: By which option to search for (default is by ID).
        :param value: The value to search for.
        :return: List of web elements denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        results = self._original_methods['find_elements'](by, value)
        # Wrap all returned elements.
        if results:
            updated_results = []
            for element in results:
                updated_results.append(EyesWebElement(element, self._eyes, self._driver))
            results = updated_results
        return results

    def click(self):
        """
        Clicks and element.
        """
        self._eyes.add_mouse_trigger_by_element('click', self)
        self.element.click()

    def send_keys(self, *value):
        """
        Sends keys to a certain element.

        :param value: The value to type into the element.
        """
        text = u''
        for val in value:
            if isinstance(val, int):
                val = val.__str__()
            text += val.encode('utf-8').decode('utf-8')
        self._eyes.add_text_trigger_by_element(self, text)
        self.element.send_keys(*value)

    def set_overflow(self, overflow, stabilization_time=None):
        """
        Sets the overflow of the current element.

        :param overflow: The overflow value to set. If the given value is None, then overflow will be set to
                         undefined.
        :param stabilization_time: The time to wait for the page to stabilize after overflow is set. If the value is
                                    None, then no waiting will take place. (Milliseconds)
        :return: The previous overflow value.
        """
        logger.debug("Setting overflow: %s" % overflow)
        if overflow is None:
            script = "var elem = arguments[0]; var origOverflow = elem.style.overflow; " \
                     "elem.style.overflow = undefined; " \
                     "return origOverflow;"
        else:
            script = "var elem = arguments[0]; var origOverflow = elem.style.overflow; " \
                     "elem.style.overflow = \"{0}\"; " \
                     "return origOverflow;".format(overflow)
        # noinspection PyUnresolvedReferences
        original_overflow = self._driver.execute_script(script, self.element)
        logger.debug("Original overflow: %s" % original_overflow)
        if stabilization_time is not None:
            time.sleep(stabilization_time / 1000)
        return original_overflow

    def hide_scrollbars(self):
        """
        Hides the scrollbars of the current element.

        :return: The previous value of the overflow property (could be None).
        """
        logger.debug('EyesWebElement.HideScrollbars()')
        return self.set_overflow('hidden')


class _EyesSwitchTo(object):
    """
    Wraps a selenium "SwitchTo" object, so we can keep track of switching between frames.
    """
    _READONLY_PROPERTIES = ['alert', 'active_element']
    PARENT_FRAME = 1

    def __init__(self, driver, switch_to):
        """
        Ctor.

        :param driver: EyesWebDriver instance.
        :param switch_to: Selenium switchTo object.
        """
        self._switch_to = switch_to
        self._driver = driver
        general_utils.create_proxy_interface(self, switch_to, self._READONLY_PROPERTIES)

    def frame(self, frame_reference):
        """
        Switch to a given frame.

        :param frame_reference: The reference to the frame.
        """
        # Find the frame's location and add it to the current driver offset
        if isinstance(frame_reference, str):
            frame_element = self._driver.find_element_by_name(frame_reference)
        elif isinstance(frame_reference, int):
            frame_elements_list = self._driver.find_elements_by_css_selector('frame, iframe')
            frame_element = frame_elements_list[frame_reference]
        else:
            # It must be a WebElement
            if isinstance(frame_reference, EyesWebElement):
                frame_reference = frame_reference.element
            frame_element = frame_reference
        # Calling the underlying "SwitchTo" object
        # noinspection PyProtectedMember
        self._driver._will_switch_to(frame_reference, frame_element)
        self._switch_to.frame(frame_reference)

    def frames(self, frame_chain):
        """
        Switches to the frames one after the other.

        :param frame_chain: A list of frames.
        """
        for frame in frame_chain:
            self._driver.set_position(frame.parent_scroll_position)
            self.frame(frame.reference)

    def default_content(self):
        """
        Switch to default content.
        """
        # We should only do anything if we're inside a frame.
        if self._driver.get_frame_chain():
            # This call resets the driver's current frame location
            # noinspection PyProtectedMember
            self._driver._will_switch_to(None)
            self._switch_to.default_content()

    def parent_frame(self):
        """
        Switch to parent frame.
        """
        # IMPORTANT We implement switching to parent frame ourselves here, since it's not yet
        # implemented by the webdriver.

        # Notice that this is a COPY of the frames.
        frames = self._driver.get_frame_chain()
        if frames:
            frames.pop()

            # noinspection PyProtectedMember
            self._driver._will_switch_to(_EyesSwitchTo.PARENT_FRAME)

            self.default_content()
            self.frames(frames)


    def window(self, window_name):
        """
        Switch to window.

        :param window_name: The window name to switch to.
        :return:The switched to window object.
        """
        # noinspection PyProtectedMember
        self._driver._will_switch_to(None)
        return self._switch_to.window(window_name)


class EyesFrame(object):
    """
    Encapsulates data about frames.
    """

    @staticmethod
    def is_same_frame_chain(frame_chain1, frame_chain2):
        """
        Checks whether the two frame chains are the same or not.

        :param frame_chain1: list of _EyesFrame instances, which represents a path to a frame.
        :param frame_chain2: list of _EyesFrame instances, which represents a path to a frame.
        :return: True if the frame chains ids are identical, otherwise False.
        """
        cl1, cl2 = len(frame_chain1), len(frame_chain2)
        if cl1 != cl2:
            return False
        for i in range(cl1):
            if frame_chain1[i].id_ != frame_chain2[i].id_:
                return False
        return True

    def __init__(self, reference, location, size, id_, parent_scroll_position):
        """
        Ctor.

        :param reference: The reference to the frame.
        :param location: The location of the frame.
        :param size: The size of the frame.
        :param id_: The id of the frame.
        :param parent_scroll_position: The parents' scroll position.
        """
        self.reference = reference
        self.location = location
        self.size = size
        self.id_ = id_
        self.parent_scroll_position = parent_scroll_position

    def clone(self):
        """
        Clone the EyesFrame object.

        :return: A cloned EyesFrame object.
        """
        return EyesFrame(self.reference, self.location.copy(), self.size.copy(), self.id_,
                         self.parent_scroll_position.clone())


class EyesWebDriver(object):
    """
    A wrapper for selenium web driver which creates wrapped elements, and notifies us about
    events / actions.
    """
    # Properties require special handling since even testing if they're callable "activates"
    # them, which makes copying them automatically a problem.
    _READONLY_PROPERTIES = ['application_cache', 'current_url', 'current_window_handle',
                            'desired_capabilities', 'log_types', 'name', 'page_source', 'title',
                            'window_handles', 'switch_to', 'mobile', 'current_context', 'context',
                            'current_activity', 'network_connection', 'available_ime_engines',
                            'active_ime_engine', 'device_time', 'w3c']
    _SETTABLE_PROPERTIES = ['orientation']

    # This should pretty much cover all scroll bars (and some fixed position footer elements :) ).
    _MAX_SCROLL_BAR_SIZE = 50

    _MIN_SCREENSHOT_PART_HEIGHT = 10

    def __init__(self, driver, eyes, stitch_mode=StitchMode.Scroll):
        """
        Ctor.

        :param driver: EyesWebDriver instance.
        :param eyes: A Eyes sdk instance.
        :param stitch_mode: How to stitch a page (default is with scrolling).
        """
        self.driver = driver
        self._eyes = eyes
        self._origin_position_provider = build_position_provider_for(StitchMode.Scroll, driver)
        self._position_provider = build_position_provider_for(stitch_mode, driver)
        # List of frames the user switched to, and the current offset, so we can properly
        # calculate elements' coordinates
        self._frames = []
        driver_takes_screenshot = driver.capabilities.get('takesScreenshot', False)

        # Creating the rest of the driver interface by simply forwarding it to the underlying
        # driver.
        general_utils.create_proxy_interface(self, driver,
                                             self._READONLY_PROPERTIES + self._SETTABLE_PROPERTIES)

        for attr in self._READONLY_PROPERTIES:
            if not hasattr(self.__class__, attr):
                setattr(self.__class__, attr, general_utils.create_proxy_property(attr, 'driver'))
        for attr in self._SETTABLE_PROPERTIES:
            if not hasattr(self.__class__, attr):
                setattr(self.__class__, attr, general_utils.create_proxy_property(attr, 'driver', True))

    def get_display_rotation(self):
        """
        Get the rotation of the screenshot.

        :return: The rotation of the screenshot we get from the webdriver in (degrees).
        """
        if self.get_platform_name() == 'Android' and self.driver.orientation == "LANDSCAPE":
            return -90
        return 0

    def get_platform_name(self):
        """
        Get the platform running the application.

        :return: The platform running the application under test.
        """
        try:
            return self.driver.desired_capabilities['platformName']
        except KeyError:
            return None

    def get_platform_version(self):
        """
        Get the platform version.

        :return: The platform version.
        """
        try:
            return str(self.driver.desired_capabilities['platformVersion'])
        except KeyError:
            return None

    def is_mobile_device(self):
        """
        Returns whether the platform running is a mobile device or not.

        :return: True if the platform running the test is a mobile platform. False otherwise.
        """
        return isinstance(self.driver, appium.webdriver.Remote)

    def get(self, url):
        """
        Navigates the driver to the given url.

        :param url: The url to navigate to.
        :return: A driver that navigated to the given url.
        """
        # We're loading a new page, so the frame location resets
        self._frames = []
        return self.driver.get(url)

    def find_element(self, by=By.ID, value=None):
        """
        Returns a WebElement denoted by "By".

        :param by: By which option to search for (default is by ID).
        :param value: The value to search for.
        :return: A element denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        result = self.driver.find_element(by, value)
        # Wrap the element.
        if result:
            result = EyesWebElement(result, self._eyes, self)
        return result

    def find_elements(self, by=By.ID, value=None):
        """
        Returns a list of web elements denoted by "By".

        :param by: By which option to search for (default is by ID).
        :param value: The value to search for.
        :return: List of elements denoted by "By".
        """
        # Get result from the original implementation of the underlying driver.
        results = self.driver.find_elements(by, value)
        # Wrap all returned elements.
        if results:
            updated_results = []
            for element in results:
                updated_results.append(EyesWebElement(element, self._eyes, self))
            results = updated_results
        return results

    def find_element_by_id(self, id_):
        """
        Finds an element by id.

        :params id_: The id of the element to be found.
        """
        return self.find_element(by=By.ID, value=id_)

    def find_elements_by_id(self, id_):
        """
        Finds multiple elements by id.

        :param id_: The id of the elements to be found.
        """
        return self.find_elements(by=By.ID, value=id_)

    def find_element_by_xpath(self, xpath):
        """
        Finds an element by xpath.

        :param xpath: The xpath locator of the element to find.
        """
        return self.find_element(by=By.XPATH, value=xpath)

    def find_elements_by_xpath(self, xpath):
        """
        Finds multiple elements by xpath.

        :param xpath: The xpath locator of the elements to be found.
        """
        return self.find_elements(by=By.XPATH, value=xpath)

    def find_element_by_link_text(self, link_text):
        """
        Finds an element by link text.

        :param link_text: The text of the element to be found.
        """
        return self.find_element(by=By.LINK_TEXT, value=link_text)

    def find_elements_by_link_text(self, text):
        """
        Finds elements by link text.

        :param text: The text of the elements to be found.
        """
        return self.find_elements(by=By.LINK_TEXT, value=text)

    def find_element_by_partial_link_text(self, link_text):
        """
        Finds an element by a partial match of its link text.

        :param link_text: The text of the element to partially match on.
        """
        return self.find_element(by=By.PARTIAL_LINK_TEXT, value=link_text)

    def find_elements_by_partial_link_text(self, link_text):
        """
        Finds elements by a partial match of their link text.

        :param link_text: The text of the element to partial match on.
        """
        return self.find_elements(by=By.PARTIAL_LINK_TEXT, value=link_text)

    def find_element_by_name(self, name):
        """
        Finds an element by name.

        :param name: The name of the element to find.
        """
        return self.find_element(by=By.NAME, value=name)

    def find_elements_by_name(self, name):
        """
        Finds elements by name.

        :param name: The name of the elements to find.
        """
        return self.find_elements(by=By.NAME, value=name)

    def find_element_by_tag_name(self, name):
        """
        Finds an element by tag name.

        :param name: The tag name of the element to find.
        """
        return self.find_element(by=By.TAG_NAME, value=name)

    def find_elements_by_tag_name(self, name):
        """
        Finds elements by tag name.

        :param name: The tag name to use when finding elements.
        """
        return self.find_elements(by=By.TAG_NAME, value=name)

    def find_element_by_class_name(self, name):
        """
        Finds an element by class name.

        :param name: The class name of the element to find.
        """
        return self.find_element(by=By.CLASS_NAME, value=name)

    def find_elements_by_class_name(self, name):
        """
        Finds elements by class name.

        :param name: The class name of the elements to find.
        """
        return self.find_elements(by=By.CLASS_NAME, value=name)

    def find_element_by_css_selector(self, css_selector):
        """
        Finds an element by css selector.

        :param css_selector: The css selector to use when finding elements.
        """
        return self.find_element(by=By.CSS_SELECTOR, value=css_selector)

    def find_elements_by_css_selector(self, css_selector):
        """
        Finds elements by css selector.

        :param css_selector: The css selector to use when finding elements.
        """
        return self.find_elements(by=By.CSS_SELECTOR, value=css_selector)

    def get_screenshot_as_base64(self):
        """
        Gets the screenshot of the current window as a base64 encoded string
           which is useful in embedded images in HTML.
        """
        screenshot64 = self.driver.get_screenshot_as_base64()
        display_rotation = self.get_display_rotation()
        if display_rotation != 0:
            logger.info('Rotation required.')
            num_quadrants = int(-(display_rotation / 90))
            logger.debug('decoding base64...')
            screenshot_bytes = base64.b64decode(screenshot64)
            logger.debug('Done! Creating image object...')
            screenshot = _image_utils.png_image_from_bytes(screenshot_bytes)
            logger.debug('Done! Rotating...')
            screenshot.quadrant_rotate(num_quadrants)
            screenshot64 = screenshot.get_base64()
        return screenshot64

    def extract_full_page_width(self):
        """
        Extracts the full page width.

        :return: The width of the full page.
        """
        # noinspection PyUnresolvedReferences
        default_scroll_width = int(round(self.execute_script(
            "return document.documentElement.scrollWidth")))
        body_scroll_width = int(round(self.execute_script("return document.body.scrollWidth")))
        return max(default_scroll_width, body_scroll_width)

    def extract_full_page_height(self):
        """
        Extracts the full page height.

        :return: The height of the full page.
        IMPORTANT: Notice there's a major difference between scrollWidth and scrollHeight.
        While scrollWidth is the maximum between an element's width and its content width,
        scrollHeight might be smaller(!) than the clientHeight, which is why we take the
        maximum between them.
        """
        # noinspection PyUnresolvedReferences
        default_client_height = int(round(self.execute_script(
            "return document.documentElement.clientHeight")))
        # noinspection PyUnresolvedReferences
        default_scroll_height = int(round(self.execute_script(
            "return document.documentElement.scrollHeight")))
        # noinspection PyUnresolvedReferences
        body_client_height = int(round(self.execute_script("return document.body.clientHeight")))
        # noinspection PyUnresolvedReferences
        body_scroll_height = int(round(self.execute_script("return document.body.scrollHeight")))
        max_document_element_height = max(default_client_height, default_scroll_height)
        max_body_height = max(body_client_height, body_scroll_height)
        return max(max_document_element_height, max_body_height)

    def get_current_position(self):
        """
        Extracts the current scroll position from the browser.

        :return: The scroll position.
        """
        return self._position_provider.get_current_position()

    def scroll_to(self, point):
        """
        Commands the browser to scroll to a given position.

        :param point: The point to scroll to.
        """
        self._position_provider.set_position(point)

    def get_entire_page_size(self):
        """
        Extracts the size of the current page from the browser using Javascript.

        :return: The page width and height.
        """
        return {'width': self.extract_full_page_width(),
                'height': self.extract_full_page_height()}

    def set_overflow(self, overflow, stabilization_time=None):
        """
        Sets the overflow of the current context's document element.

        :param overflow: The overflow value to set. If the given value is None, then overflow will be set to
                         undefined.
        :param stabilization_time: The time to wait for the page to stabilize after overflow is set. If the value is
                                    None, then no waiting will take place. (Milliseconds)
        :return: The previous overflow value.
        """
        logger.debug("Setting overflow: %s" % overflow)
        if overflow is None:
            script = "var origOverflow = document.documentElement.style.overflow; " \
                     "document.documentElement.style.overflow = undefined; " \
                     "return origOverflow;"
        else:
            script = "var origOverflow = document.documentElement.style.overflow; " \
                     "document.documentElement.style.overflow = \"{0}\"; " \
                     "return origOverflow;".format(overflow)
        # noinspection PyUnresolvedReferences
        original_overflow = self.execute_script(script)
        logger.debug("Original overflow: %s" % original_overflow)
        if stabilization_time is not None:
            time.sleep(stabilization_time / 1000)
        return original_overflow

    def wait_for_page_load(self, timeout=3, throw_on_timeout=False):
        """
        Waits for the current document to be "loaded".

        :param timeout: The maximum time to wait, in seconds.
        :param throw_on_timeout: Whether to throw an exception when timeout is reached.
        """
        # noinspection PyBroadException
        try:
            WebDriverWait(self.driver, timeout)\
                .until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
        except:
            logger.debug('Page load timeout reached!')
            if throw_on_timeout:
                raise

    def hide_scrollbars(self):
        """
        Hides the scrollbars of the current context's document element.

        :return: The previous value of the overflow property (could be None).
        """
        logger.debug('HideScrollbars() called. Waiting for page load...')
        self.wait_for_page_load()
        logger.debug('About to hide scrollbars')
        return self.set_overflow('hidden')

    def get_frame_chain(self):
        """
        Gets the frame chain.

        :return: A list of EyesFrame instances which represents the path to the current frame.
            This can later be used as an argument to _EyesSwitchTo.frames().
        """
        return [frame.clone() for frame in self._frames]

    def get_viewport_size(self):
        """
        Returns:
            The viewport size of the current frame.
        """
        return _viewport_size.get_viewport_size(self)

    def get_default_content_viewport_size(self):
        """
        Gets the viewport size.

        :return: The viewport size of the most outer frame.
        """
        current_frames = self.get_frame_chain()
        # If we're inside a frame, then we should first switch to the most outer frame.
        self.switch_to.default_content()
        viewport_size = _viewport_size.get_viewport_size(self)
        self.switch_to.frames(current_frames)
        return viewport_size

    def reset_origin(self):
        """
        Reset the origin position to (0, 0).

        :raise EyesError: Couldn't scroll to position (0, 0).
        """
        self._origin_position_provider.push_state()
        self._origin_position_provider.set_position(Point(0, 0))
        current_scroll_position = self._origin_position_provider.get_current_position()
        if current_scroll_position.x != 0 or current_scroll_position.y != 0:
            self._origin_position_provider.pop_state()
            raise EyesError("Couldn't scroll to the top/left part of the screen!")

    def restore_origin(self):
        """
        Restore the origin position.
        """
        self._origin_position_provider.pop_state()

    def save_position(self):
        """
        Saves the position in the _position_provider list.
        """
        self._position_provider.push_state()

    def restore_position(self):
        """
        Restore the position.
        """
        self._position_provider.pop_state()

    @staticmethod
    def _wait_before_screenshot(seconds):
        logger.debug("Waiting {} ms before taking screenshot..".format(int(seconds*1000)))
        time.sleep(seconds)
        logger.debug("Finished waiting!")

    def get_full_page_screenshot(self, wait_before_screenshots):
        """
        Gets a full page screenshot.

        :param wait_before_screenshots: (float) Seconds to wait before taking each screenshot.
        :return: The full page screenshot.
        """
        logger.info('getting full page screenshot..')

        # Saving the current frame reference and moving to the outermost frame.
        original_frame = self.get_frame_chain()
        self.switch_to.default_content()

        self.reset_origin()

        entire_page_size = self.get_entire_page_size()

        # Starting with the screenshot at 0,0
        EyesWebDriver._wait_before_screenshot(wait_before_screenshots)
        part64 = self.get_screenshot_as_base64()
        screenshot = _image_utils.png_image_from_bytes(base64.b64decode(part64))

        # IMPORTANT This is required! Since when calculating the screenshot parts for full size,
        # we use a screenshot size which is a bit smaller (see comment below).
        if (screenshot.width >= entire_page_size['width']) and \
                (screenshot.height >= entire_page_size['height']):
            self.restore_origin()
            self.switch_to.frames(original_frame)
            return screenshot

        #  We use a smaller size than the actual screenshot size in order to eliminate duplication
        #  of bottom scroll bars, as well as footer-like elements with fixed position.
        screenshot_part_size = {'width': screenshot.width,
                                'height': max(screenshot.height - self._MAX_SCROLL_BAR_SIZE,
                                              self._MIN_SCREENSHOT_PART_HEIGHT)}

        logger.debug("Total size: {0}, Screenshot part size: {1}".format(entire_page_size,
                                                                         screenshot_part_size))

        entire_page = Region(0, 0, entire_page_size['width'], entire_page_size['height'])
        screenshot_parts = entire_page.get_sub_regions(screenshot_part_size)

        # Starting with the screenshot we already captured at (0,0).
        stitched_image = screenshot

        self.save_position()

        for part in screenshot_parts:
            # Since we already took the screenshot for 0,0
            if part.left == 0 and part.top == 0:
                logger.debug('Skipping screenshot for 0,0 (already taken)')
                continue
            logger.debug("Taking screenshot for {0}".format(part))
            # Scroll to the part's top/left and give it time to stabilize.
            self.scroll_to(Point(part.left, part.top))
            EyesWebDriver._wait_before_screenshot(wait_before_screenshots)
            # Since screen size might cause the scroll to reach only part of the way
            current_scroll_position = self.get_current_position()
            logger.debug("Scrolled To ({0},{1})".format(current_scroll_position.x,
                                                        current_scroll_position.y))
            part64 = self.get_screenshot_as_base64()
            part_image = _image_utils.png_image_from_bytes(base64.b64decode(part64))
            stitched_image.paste(current_scroll_position.x, current_scroll_position.y,
                                 part_image.pixel_bytes)

        self.restore_position()
        self.restore_origin()
        self.switch_to.frames(original_frame)

        return stitched_image

    def _will_switch_to(self, frame_reference, frame_element=None):
        """
        Updates the current webdriver that a switch was made to a frame element.

        :param frame_reference: The reference to the frame.
        :param frame_element: The frame element instance.
        """
        if frame_element is not None:
            frame_location = frame_element.location
            frame_size = frame_element.size
            frame_id = frame_element.id
            parent_scroll_position = self.get_current_position()
            # Frame border can affect location calculation for elements.
            # noinspection PyBroadException
            try:
                frame_left_border_width = int(frame_element
                                              .value_of_css_property('border-left-width')
                                              .rstrip('px'))
                frame_top_border_width = int(frame_element.value_of_css_property('border-top-width')
                                             .rstrip('px'))
            except:
                frame_left_border_width = 0
                frame_top_border_width = 0
            frame_location['x'] += frame_left_border_width
            frame_location['y'] += frame_top_border_width
            self._frames.append(EyesFrame(frame_reference, frame_location, frame_size, frame_id,
                                          parent_scroll_position))
        elif frame_reference == _EyesSwitchTo.PARENT_FRAME:
            self._frames.pop()
        else:
            # We moved out of the frames
            self._frames = []

    @property
    def switch_to(self):
        return _EyesSwitchTo(self, self.driver.switch_to)

    @property
    def current_offset(self):
        """
        Return the current offset of the context we're in (e.g., due to switching into frames)
        """
        offset = {'x': 0, 'y': 0}
        for frame in self._frames:
            offset['x'] += frame.location['x']
            offset['y'] += frame.location['y']
        return offset


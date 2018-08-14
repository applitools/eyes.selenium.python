import typing as tp
import base64

from selenium.common.exceptions import WebDriverException

from ..core import EyesError, Point, Region, OutOfBoundsError
from ..utils import image_utils

if tp.TYPE_CHECKING:
    from PIL import Image


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
        # type: (Image.Image, EyesWebDriver) -> EyesScreenshot
        """
        Creates an instance from the base64 data.

        :param screenshot: The screenshot image.
        :param driver: The webdriver for the session.
        """
        return EyesScreenshot(driver, screenshot=screenshot)

    def __init__(self, driver, screenshot=None, screenshot64=None,
                 is_viewport_screenshot=None, frame_location_in_screenshot=None):
        # type: (EyesWebDriver, PngImage, None, tp.Optional[bool], tp.Optional[Point]) -> None
        """
        Initializes a Screenshot instance. Either screenshot or screenshot64 must NOT be None.
        Should not be used directly. Use create_from_image/create_from_base64 instead.

        :param driver: EyesWebDriver instance which handles the session from which the screenshot
                    was retrieved.
        :param screenshot: image instance. If screenshot64 is None,
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
            self._screenshot = image_utils.image_from_bytes(base64.b64decode(screenshot64))
        else:
            raise EyesError("both screenshot and screenshot64 are None!")
        self._driver = driver
        self._viewport_size = driver.get_default_content_viewport_size()  # type: ViewPort

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
        except (WebDriverException, EyesError):
            self._scroll_position = Point(0, 0)
        if is_viewport_screenshot is None:
            is_viewport_screenshot = (self._screenshot.width <= self._viewport_size['width']
                                      and self._screenshot.height <= self._viewport_size['height'])
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
        # type: (tp.List[EyesFrame], tp.Optional[bool]) -> Point
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
        # type: () -> tp.List[EyesFrame]
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
            self._screenshot64 = image_utils.get_base64(self._screenshot)
        return self._screenshot64

    def get_bytes(self):
        # type: () -> bytes
        """
        Returns the bytes of the screenshot.

        :return: The bytes representation of the png.
        """
        return image_utils.get_bytes(self._screenshot)

    def get_location_relative_to_frame_viewport(self, location):
        # type: (tp.Dict[tp.Text, Num]) -> tp.Dict[tp.Text, Num]
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
        # type: (AnyWebElement) -> Region
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
        # type: (Region) -> Region
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
        # type: (Region) -> EyesScreenshot
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

        screenshot = image_utils.get_image_part(self._screenshot, sub_screenshot_region)
        return EyesScreenshot(self._driver, screenshot,
                              is_viewport_screenshot=self._is_viewport_screenshot,
                              frame_location_in_screenshot=sub_screenshot_frame_location)

    def get_sub_screenshot_by_element(self, element):
        # type: (EyesWebElement) -> EyesScreenshot
        """
        Gets the element's region part of the screenshot image.

        :param element: The element in the frame.
        :return: A screenshot object representing the element's region part of the
            image.
        """
        element_region = self.get_element_region_in_frame_viewport(element)
        return self.get_sub_screenshot_by_region(element_region)

    def get_viewport_screenshot(self):
        # type: () -> EyesScreenshot
        """
        Always return viewport size screenshot
        """
        # if screenshot if full page
        if not self._is_viewport_screenshot and not self._driver.is_mobile_device():
            return self.get_sub_screenshot_by_region(
                Region(top=self._scroll_position.y, height=self._viewport_size['height'],
                       width=self._viewport_size['width']))
        return self

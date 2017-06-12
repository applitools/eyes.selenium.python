from applitools.errors import EyesError
from applitools.geometry import Region


# Ignore regions related classes.

class IgnoreRegionByElement(object):
    def __init__(self, element):
        self.element = element

    def get_region(self, driver, eyes_screenshot):
        return eyes_screenshot.get_element_region_in_frame_viewport(self.element)


class IgnoreRegionBySelector(object):
    def __init__(self, by, value):
        """
        :param by: (selenium.webdriver.common.by.By) The "by" part of a selenium selector for an element which
            represents the ignore region
        :param value: (str) The "value" part of a selenium selector for an element which represents the ignore region.
        """
        self.by = by
        self.value = value

    def get_region(self, driver, eyes_screenshot):
        element = driver.find_element(self.by, self.value)
        return eyes_screenshot.get_element_region_in_frame_viewport(element)


class _NopRegionWrapper(object):
    def __init__(self, region):
        self.region = region

    def get_region(self, driver, eyes_screenshot):
        return self.region


# Floating regions related classes.

class FloatingBounds(object):
    def __init__(self, max_left_offset=0, max_up_offset=0, max_right_offset=0, max_down_offset=0):
        self.max_left_offset = max_left_offset
        self.max_up_offset = max_up_offset
        self.max_right_offset = max_right_offset
        self.max_down_offset = max_down_offset


class FloatingRegion(object):
    def __init__(self, region, bounds):
        """
        :param region: (Region) The inner region (the floating part).
        :param bounds: (FloatingBounds) The outer rectangle bounding the inner region.
        """
        self.region = region
        self.bounds = bounds

    def get_region(self, driver, eyes_screenshot):
        """Used for compatibility when iterating over regions"""
        return self

    def __getstate__(self):
        return dict(top=self.region.top,
                    left=self.region.left,
                    width=self.region.width,
                    height=self.region.height,
                    maxLeftOffset=self.bounds.max_left_offset,
                    maxUpOffset=self.bounds.max_up_offset,
                    maxRightOffset=self.bounds.max_right_offset,
                    maxDownOffset=self.bounds.max_down_offset)

    # This is required in order for jsonpickle to work on this object.
    # noinspection PyMethodMayBeStatic
    def __setstate__(self, state):
        raise EyesError('Cannot create FloatingRegion instance from dict!')


class FloatingRegionByElement(object):
    def __init__(self, element, bounds):
        """
        :param element: (WebElement|EyesWebElement) The element which represents the inner region (the floating part).
        :param bounds: (FloatingBounds) The outer rectangle bounding the inner region.
        """
        self.element = element
        self.bounds = bounds

    def get_region(self, driver, eyes_screenshot):
        region = eyes_screenshot.get_element_region_in_frame_viewport(self.element)
        return FloatingRegion(region, self.bounds)


class FloatingRegionBySelector(object):
    def __init__(self, by, value, bounds):
        """
        :param by: (selenium.webdriver.common.by.By) The "by" part of a selenium selector for an element which
            represents the inner region
        :param value: (str) The "value" part of a selenium selector for an element which represents the inner region.
        :param bounds: (FloatingBounds) The outer rectangle bounding the inner region.
        """
        self.by = by
        self.value = value
        self.bounds = bounds

    def get_region(self, driver, eyes_screenshot):
        element = driver.find_element(self.by, self.value)
        region = eyes_screenshot.get_element_region_in_frame_viewport(element)
        return FloatingRegion(region, self.bounds)


# Main class for the module
class Target(object):
    """
    Target for an eyes.check_window/region.
    """
    def __init__(self):
        self._ignore_caret = False
        self._ignore_regions = []
        self._floating_regions = []

    def ignore(self, *regions):
        """
        Add ignore regions to this target.
        :param regions: Ignore regions to add. Can be of several types:
            (Region) Region specified by coordinates
            (IgnoreRegionBySelector) Region specified by a selector of an element
            (IgnoreRegionByElement) Region specified by a WebElement instance.
        :return: (Target) self.
        """
        for region in regions:
            if region is None:
                continue
            if isinstance(region, Region):
                self._ignore_regions.append(_NopRegionWrapper(region))
            else:
                self._ignore_regions.append(region)
        return self

    def floating(self, *regions):
        """
        Add floating regions to this target.
        :param regions: Floating regions to add. Can be of several types:
            (Region) Region specified by coordinates
            (FloatingRegionByElement) Region specified by a WebElement instance.
            (FloatingRegionBySelector) Region specified by a selector of an element
        :return: (Target) self.
        """
        for region in regions:
            if region is None:
                continue
            self._floating_regions.append(region)
        return self

    def ignore_caret(self, ignore=True):
        """
        Whether we should ignore caret when matching screenshots.
        :param ignore: (boolean)
        :return: (Target) self
        """
        self._ignore_caret = ignore
        return self

    def get_ignore_caret(self):
        return self._ignore_caret

    @property
    def ignore_regions(self):
        """The ignore regions defined on the current target."""
        return self._ignore_regions

    @property
    def floating_regions(self):
        """The floating regions defined on the current target."""
        return self._floating_regions


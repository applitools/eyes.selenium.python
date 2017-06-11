from applitools.geometry import Region


# Ignore regions related classes.

class IgnoreRegionByElement(object):
    def __init__(self, element):
        self.element = element

    def get_region(self, driver, eyes_screenshot):
        return eyes_screenshot.get_element_region_in_frame_viewport(self.element)


class IgnoreRegionBySelector(object):
    def __init__(self, selector):
        self.selector = selector

    def get_region(self, driver, eyes_screenshot):
        element = driver.find(self.selector['by'], self.selector['value'])
        return eyes_screenshot.get_element_region_in_frame_viewport(element)


class _NopRegionWrapper(object):
    def __init__(self, region):
        self.region = region

    def get_region(self, driver, eyes_screenshot):
        return self.region


# Floating regions related classes.

class FloatingRegion(object):
    def __init__(self, region, bounds):
        self.region = region
        self.bounds = bounds


class FloatingRegionByElement(object):
    def __init__(self, element, bounds):
        self.element = element
        self.bounds = bounds

    def get_region(self, driver, eyes_screenshot):
        region = eyes_screenshot.get_element_region_in_frame_viewport(self.element)
        return FloatingRegion(region, self.bounds)


class FloatingRegionBySelector(object):
    def __init__(self, selector, bounds):
        self.selector = selector
        self.bounds = bounds

    def get_region(self, driver, eyes_screenshot):
        element = driver.find(self.selector['by'], self.selector['value'])
        region = eyes_screenshot.get_element_region_in_frame_viewport(element)
        return FloatingRegion(region, self.bounds)


# Main class for the module
class Target(object):
    """
    Target for an eyes.check_window/region.
    """
    def __init__(self):
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
            self._ignore_regions.append(region)
        return self

    @property
    def ignore_regions(self):
        """The ignore regions defined on the current target."""
        return self._ignore_regions

    @property
    def floating_regions(self):
        """The floating regions defined on the current target."""
        return self._floating_regions


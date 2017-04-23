import math
from collections import OrderedDict
from applitools.errors import EyesError


class Point:
    """
    A point with the coordinates (x,y).
    """

    def __init__(self, x=0, y=0):
        self.x = int(round(x))
        self.y = int(round(y))

    def __getstate__(self):
        return {"x": self.x, "y": self.y}

    # Required is required in order for jsonpickle to work on this object.
    # noinspection PyMethodMayBeStatic
    def __setstate__(self, state):
        raise EyesError('Cannot create Point instance from dict!')

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)

    def __div__(self, scalar):
        return Point(self.x / scalar, self.y / scalar)

    def __str__(self):
        return "({0}, {1})".format(self.x, self.y)

    def length(self):
        """
        Returns the distance from (0, 0).
        """
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def distance_to(self, p):
        """
        Calculate the distance between two points.

        :return: The distance to p.
        """
        return (self - p).length()

    def as_tuple(self):
        """
        Return the point as a tuple.

        :return: Point as tuple.
        """
        return self.x, self.y

    def clone(self):
        """
        Return a full copy of this point.

        :return: Cloned point.
        """
        return Point(self.x, self.y)

    def move_to(self, x, y):
        """
        Moves the point to new x, y.

        :param x: Coordinate x.
        :param y: Coordinate y.
        """
        self.x = x
        self.y = y

    def offset(self, dx, dy):
        """
        Move to new (x+dx,y+dy).

        :param dx: Offset to move coordinate x.
        :param dy: Offset to move coordinate y.
        """
        self.x = self.x + dx
        self.y = self.y + dy

    def rotate(self, rad):
        """
        Rotate counter-clockwise around the origin by rad radians.

        Positive y goes *up,* as in traditional mathematics.

        Interestingly, you can use this in y-down computer graphics, if
        you just remember that it turns clockwise, rather than
        counter-clockwise.

        :param rad: The radians to rotate the point.
        :return: The new position is returned as a new Point.
        """
        s, c = [f(rad) for f in (math.sin, math.cos)]
        x, y = (c * self.x - s * self.y, s * self.x + c * self.y)
        return Point(x, y)

    def rotate_about(self, p, theta):
        """
        Rotate counter-clockwise around a point, by theta degrees.

        Positive y goes *up,* as in traditional mathematics.

        The new position is returned as a new Point.

        :param p: A point to rotate around.
        :param theta: Theta degrees to rotate around.
        :return: The result of the rotation.
        """
        result = self.clone()
        result.offset(-p.x, -p.y)
        result.rotate(theta)
        result.offset(p.x, p.y)
        return result


class Region:
    """
    A rectangle identified by left,top, width, height.
    """

    def __init__(self, left=0, top=0, width=0, height=0):
        self.left = int(round(left))
        self.top = int(round(top))
        self.width = int(round(width))
        self.height = int(round(height))

    def __getstate__(self):
        return OrderedDict([("top", self.top), ("left", self.left), ("width", self.width),
                            ("height", self.height)])

    # Required is required in order for jsonpickle to work on this object.
    # noinspection PyMethodMayBeStatic
    def __setstate__(self, state):
        raise EyesError('Cannot create Region instance from dict!')

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def location(self):
        """Return the top-left corner as a Point."""
        return Point(self.left, self.top)

    @location.setter
    def location(self, p):
        """Sets the top left corner of the region"""
        self.left, self.top = p.x, p.y

    @property
    def bottom_right(self):
        """Return the bottom-right corner as a Point."""
        return Point(self.right, self.bottom)

    def clone(self):
        """
        Clone the rectangle.

        :return: The new rectangle object.
        """
        return Region(self.left, self.top, self.width, self.height)

    def is_same(self, other):
        """
        Checks whether the other rectangle has the same coordinates.

        :param other: The other rectangle to check with.
        :return: Whether or not the rectangles have same coordinates.
        """
        return self.left == other.left and self.top == other.top and self.width == other.width \
            and self.height == other.height

    def is_same_size(self, other):
        """
        Checks whether the other rectangle is the same size.

        :param other: The other rectangle to check with.
        :return: Whether or not the rectangles are the same size.
        """
        return self.width == other.width and self.height == other.height

    def make_empty(self):
        """
        Sets the current instance as an empty instance
        """
        self.left = self.top = self.width = self.height = 0

    def clip_negative_location(self):
        """
        Sets the left/top values to 0 if the value is negative
        """
        self.left = max(self.left, 0)
        self.top = max(self.top, 0)

    def is_empty(self):
        """
        Checks whether the rectangle is empty.

        :return: True if the rectangle is empty. Otherwise False.
        """
        return self.left == self.top == self.width == self.height == 0

    def contains(self, pt):
        """
        Return true if a point is inside the rectangle.

        :return: True if the point is inside the rectangle. Otherwise False.
        """
        x, y = pt.as_tuple()
        return (self.left <= x <= self.right and
                self.top <= y <= self.bottom)

    def overlaps(self, other):
        """Return true if a rectangle overlaps this rectangle."""
        return (self.left <= other.left <= self.right or other.left <= self.left <= other.right) \
            and (self.top <= other.top <= self.bottom or other.top <= self.top <= other.bottom)

    def intersect(self, other):
        # If the regions don't overlap, the intersection is empty
        if not self.overlaps(other):
            self.make_empty()
            return
        intersection_left = self.left if self.left >= other.left else other.left
        intersection_top = self.top if self.top >= other.top else other.top
        intersection_right = self.right if self.right <= other.right else other.right
        intersection_bottom = self.bottom if self.bottom <= other.bottom else other.bottom
        self.left, self.top = intersection_left, intersection_top
        self.width = intersection_right - intersection_left
        self.height = intersection_bottom - intersection_top

    def get_sub_regions(self, max_sub_region_size):
        """
        Returns a list of Region objects which compose the current region.
        """
        sub_regions = []
        current_top = self.top
        while current_top < self.height:

            current_bottom = current_top + max_sub_region_size["height"]
            if current_bottom > self.height:
                current_bottom = self.height

            current_left = self.left
            while current_left < self.width:
                current_right = current_left + max_sub_region_size["width"]
                if current_right > self.width:
                    current_right = self.width

                current_height = current_bottom - current_top
                current_width = current_right - current_left

                sub_regions.append(Region(current_left, current_top, current_width,
                                          current_height))

                current_left += max_sub_region_size["width"]

            current_top += max_sub_region_size["height"]

        return sub_regions

    @property
    def middle_offset(self):
        return Point(int(round(self.width / 2)), int(round(self.height / 2)))

    def __str__(self):
        return "(%s, %s) %s x %s" % (self.left, self.top, self.width, self.height)


EMPTY_REGION = Region()

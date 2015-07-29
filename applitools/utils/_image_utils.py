"""
Utilities for image manipulation.
"""
import base64
import copy
import io
import math
import png

from applitools import logger
from applitools.errors import EyesError
from applitools.utils import general_utils

# Python 2 / 3 compatibility
import sys

if sys.version < '3':
    range = xrange


def quadrant_rotate(m, num_quadrants):
    """
    Rotates a matrix 90 deg clockwise or counter clockwise (depending whether num_quadrants is positive or negative,
    respectively).
    :param list m: The 2D matrix to rotate.
    :param int num_quadrants: The number of rotations to perform.
    :return list: A rotated copy of the matrix.
    """
    def rotate_cw(m2):
        """
        Rotate m2 clockwise.
        :param list m2: The 2D matrix to rotate.
        :return list: The clockwise rotated matrix.
        """
        # We must use the "list" wrapper for compliance with Python 3
        return list(map(list, list(zip(*m2[::-1]))))

    def rotate_ccw(m2):
        """
        Rotate m2 counter-clockwise.
        :param list m2: The 2D matrix to rotate.
        :return list: The counter-clockwise rotated matrix.
        """
        # We must use the "list" wrapper for compliance with Python 3
        return list(map(list, list(zip(*m2))[::-1]))

    if num_quadrants == 0:
        return m
    rotate_func = rotate_cw if num_quadrants > 0 else rotate_ccw
    #Perform the rotation.
    result = m
    for i in range(abs(num_quadrants)):
        result = rotate_func(result)
    return result


def png_image_from_file(f):
    """
    Reads the PNG data from the given file stream and returns a new PngImage instance.
    """
    width, height, pixels_iterable, meta_info = png.Reader(file=f).asDirect()
    return PngImage(width, height, list(pixels_iterable), meta_info)


def png_image_from_bytes(png_bytes):
    """
    Reads the PNG data from the given file stream and returns a new PngImage instance.
    """
    width, height, pixels_iterable, meta_info = png.Reader(bytes=png_bytes).asDirect()
    return PngImage(width, height, list(pixels_iterable), meta_info)


class PngImage(object):
    """
    Encapsulates an image.
    """

    def __init__(self, width, height, pixel_bytes, meta_info):
        """
        Initializes a PngImage object.
        :param int width: The width of the image.
        :param int height: The height of the image.
        :param list pixel_bytes: The of pixel bytes of the image, as a 2D matrix (i.e, a list of rows).
        :param dict meta_info: The image meta info as given by png.Reader .
        """
        self.width = width
        self.height = height
        self.pixel_bytes = pixel_bytes
        self.meta_info = copy.copy(meta_info)
        # Images are either RGB or Greyscale
        if not meta_info["greyscale"]:
            self.pixel_size = 3
        else:
            self.pixel_size = 1
        # If there's also an alpha channel
        if meta_info["alpha"]:
            self.pixel_size += 1

    def _update_size(self, width, height):
        """
        Updates the size of the image.
        :param int width: The updated width.
        :param int height: The updated height.
        """
        self.width = int(math.ceil(width))
        self.height = int(math.ceil(height))
        self.meta_info['size'] = (self.width, self.height)

    def paste(self, left, top, pixel_bytes_to_paste):
        """
        Pastes the given pixels on the image. Expands width/height if needed. Pixel size must be
        the same as the current image's pixels.
        """
        x_start = left * self.pixel_size
        pixel_bytes_to_paste_len = len(pixel_bytes_to_paste[0])
        for y_offset in range(len(pixel_bytes_to_paste)):
            y_current = top + y_offset
            # It's okay to use self.height as a condition, even after y_current is greater
            # than it, since in this case we append to the end of the list anyway.
            if y_current < self.height:
                original_row = self.pixel_bytes[y_current]
                updated_row = original_row[:x_start] + pixel_bytes_to_paste[y_offset] + \
                    original_row[(x_start + pixel_bytes_to_paste_len):]
                self.pixel_bytes[y_current] = updated_row
            else:
                self.pixel_bytes.append(pixel_bytes_to_paste[y_offset])
        # Update the width and height if required
        paste_right = (x_start + pixel_bytes_to_paste_len) / self.pixel_size
        self._update_size(max(self.width, paste_right), len(self.pixel_bytes))

    def get_subimage(self, region):
        """
        :return PngImage:
        """
        if region.is_empty():
            raise EyesError('region is empty!')
        result_pixels = []
        x_start = region.left * self.pixel_size
        x_end = x_start + (region.width * self.pixel_size)
        y_start = region.top
        for y_offset in range(region.height):
            pixels_row = self.pixel_bytes[y_start + y_offset][x_start:x_end]
            result_pixels.append(pixels_row)
        meta_info = copy.copy(self.meta_info)
        meta_info['size'] = (region.width, region.height)
        return PngImage(region.width, region.height, result_pixels, meta_info)

    def remove_columns(self, left, count):
        """
        Removes pixels columns from the image.
        :param int left: The index of the left most column to remove.
        :param int count: The number of columns to remove.
        """
        for row_index in range(self.height):
            self.pixel_bytes[row_index] = self.pixel_bytes[row_index][:(left * self.pixel_size)] + \
                self.pixel_bytes[row_index][(left + count) * self.pixel_size:]
            # Updating the width
            self._update_size(len(self.pixel_bytes[0]) / self.pixel_size, self.height)

    def remove_rows(self, top, count):
        """
        Removes pixels rows from the image.
        :param int top: The index of the top most row to remove.
        :param int count: The number of rows to remove.
        """
        self.pixel_bytes = self.pixel_bytes[:top] + self.pixel_bytes[(top + count):]
        self._update_size(self.width, len(self.pixel_bytes))

    def get_channel(self, index):
        """
        Get the values for a specific color/alpha of the image's pixels.
        :param int index: The index of the channel we would like to get.
        :return iterable: A copy of the values for the given pixel channel.
        """
        if index > self.pixel_size-1:
            raise EyesError("Invalid channel: {}, (pixel size {})".format(index, self.pixel_size))
        return map(lambda x: list(x[0::self.pixel_size]), self.pixel_bytes)

    def quadrant_rotate(self, num_quadrants):
        """
        Rotates the image by 90 degrees clockwise or counter-clockwise.
        :param int num_quadrants: The number of rotations to perform.
        """
        # Divide the continuous sequence of bytes in each row into pixel groups (since values within a single pixel
        # should maintain order).
        logger.debug('Dividing into chunks...')
        pixels = list(map(lambda bytes_row: general_utils.divide_to_chunks(bytes_row, self.pixel_size),
                          self.pixel_bytes))
        logger.debug('Done! Rotating pixels...')
        rotated_pixels = quadrant_rotate(pixels, num_quadrants)
        logger.debug('Done! flattening chunks back to bytes...')
        # Unite the pixel groups back to continuous pixel bytes for each row.
        rotated_pixel_bytes = list(map(lambda pixels_row: general_utils.join_chunks(pixels_row), rotated_pixels))
        logger.debug('Done!')
        self.pixel_bytes = rotated_pixel_bytes
        self._update_size(len(rotated_pixel_bytes[0]) / self.pixel_size, len(rotated_pixel_bytes))

    def write(self, output):
        """
        Writes the png to the output stream.
        """
        png.Writer(**self.meta_info).write(output, self.pixel_bytes)

    def get_base64(self):
        """
        :return: The base64 representation of the PNG bytes.
        """
        image_bytes_stream = io.BytesIO()
        self.write(image_bytes_stream)
        image64 = base64.b64encode(image_bytes_stream.getvalue()).decode('utf-8')
        image_bytes_stream.close()
        return image64

    def get_bytes(self):
        """
        :return: The image PNG bytes.
        """
        image_bytes_stream = io.BytesIO()
        self.write(image_bytes_stream)
        image_bytes = image_bytes_stream.getvalue()
        image_bytes_stream.close()
        return image_bytes
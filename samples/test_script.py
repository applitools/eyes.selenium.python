import os

from applitools import logger
from applitools.eyes import Eyes
from applitools.geometry import Region
from applitools.logger import StdoutLogger

logger.set_logger(StdoutLogger())
eyes = Eyes()
eyes.api_key = os.environ['APPLITOOLS_API_KEY']

try:
    eyes.open(None, "Python Images", "First image test")
    with open("MY_IMAGE.png", 'rb') as f:
        image = f.read()
    eyes.check_image(image, None, "home")
    eyes.check_image(image, Region(left=1773, top=372, width=180, height=220), "Bada region")
    eyes.close()
finally:
    eyes.abort_if_not_closed()

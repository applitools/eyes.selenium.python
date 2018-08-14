from .common import StitchMode
from .__version__ import __version__

from .core import *
from .selenium import *
from .utils import *

# for backward compatibility
from .core import errors, geometry, target
from .selenium import eyes

__all__ = (
        core.__all__ +
        selenium.__all__ +
        utils.__all__ +
        ('errors', 'geometry', 'target', 'StitchMode', 'eyes')
)

# for backward compability
VERSION = __version__

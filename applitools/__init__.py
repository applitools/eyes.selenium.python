from .__version__ import __version__
from .core import *  # noqa
from .selenium import *  # noqa
from .utils import *  # noqa

# for backward compatibility
from .core import errors, geometry  # noqa
from .selenium import eyes, target  # noqa

__all__ = (
        core.__all__ +  # noqa
        selenium.__all__ +  # noqa
        utils.__all__ +  # noqa
        ('errors', 'geometry', 'target', 'StitchMode', 'eyes')
)

# for backward compatibility
VERSION = __version__

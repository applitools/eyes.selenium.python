import glob
import sys

modules = glob.glob('*.py')
try:
    modules.remove('__init__.py')
except ValueError:
    pass

__all__ = ['utils'] + modules

VERSION = '3.11.3'
PY34 = sys.version_info >= (3, 4)
PY35 = sys.version_info >= (3, 5)

import glob

modules = glob.glob('*.py')
try:
    modules.remove('__init__.py')
except ValueError:
    pass

__all__ = ['utils'] + modules

VERSION = '3.10.3'


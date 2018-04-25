"""
Compatibility layer between Python 2 and 3
"""
import abc
import sys


PY3 = sys.version_info >= (3,)

if PY3:
    ABC = abc.ABC
    range = range  # type: ignore
else:
    ABC = abc.ABCMeta(str("ABC"), (), {})
    range = xrange  # type: ignore

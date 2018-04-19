"""
Compatibility layer between Python 2 and 3
"""
import abc
import sys

from applitools import PY34

if PY34:
    ABC = abc.ABC
    range = range  # type: ignore
else:
    ABC = abc.ABCMeta(str("ABC"), (), {})
    range = xrange  # type: ignore

"""
Compatibility layer between Python 2 and 3
"""
import abc
import sys

if sys.version_info >= (3, 4):
    ABC = abc.ABC
    range = range
else:
    ABC = abc.ABCMeta(str("ABC"), (), {})
    range = xrange

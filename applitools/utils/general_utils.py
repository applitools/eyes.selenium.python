"""
General purpose utilities.
"""
from datetime import tzinfo, timedelta
import json
import types

# Python 2 / 3 compatibility
import sys

if sys.version < '3':
    range = xrange


class _UtcTz(tzinfo):
    """A UTC timezone class which is tzinfo compliant."""
    _ZERO = timedelta(0)

    def utcoffset(self, dt):
        return _UtcTz._ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return _UtcTz._ZERO

# Constant representing UTC
UTC = _UtcTz()


def to_json(obj):
    """
    Returns an object's json representation (defaults to __getstate__ for user defined types).
    """
    return json.dumps(obj, default=lambda o: o.__getstate__(), indent=4)


def public_state_to_json(obj):
    """
    Returns an object's json representation, without(!) its private variables.
    DO NOT USE! This method has a problem with "datetime" objects (which have no __dict__
    attribute).
    """
    def get_public_state(o):
        return {key: value for key, value in o.__dict__.items()
                if not callable(value) and not key.startswith('_')}

    return json.dumps(obj, default=lambda o: get_public_state(o), indent=4)


def divide_to_chunks(l, chunk_size):
    """
    Divides a list into chunks.
    :param iterable l: The list to divide.
    :param int chunk_size: The size of each chunk
    :return list: A list of lists. Each internal list has a maximum size of chunk_size (last item might be shorter).
    """
    result = []
    for i in range(0, len(l), chunk_size):
        result.extend([l[i:i + chunk_size]])
    return result


def join_chunks(l):
    """
    Joins a list of chunks into a single continuous list of values.
    :param iterable l: The list of chunks to join.
    :return list: A single composed the concatenated values of the chunks.
    """
    result = []
    for i in l:
        result.extend(i)
    return result


def create_proxy_property(property_name, target_name, is_settable=False):
    """
    Returns a property object which forwards "name" to target.
    """
    # noinspection PyUnusedLocal
    def _proxy_get(self):
        return getattr(getattr(self, target_name), property_name)

    # noinspection PyUnusedLocal
    def _proxy_set(self, val):
        return setattr(getattr(self, target_name), property_name, val)

    if not is_settable:
        return property(_proxy_get)
    else:
        return property(_proxy_get, _proxy_set)


def create_forwarded_method(from_, to, func_name):
    """
    Returns a method(!) to be set on 'from_', which activates 'func_name' on 'to'.
    """
    # noinspection PyUnusedLocal
    def forwarded_method(self_, *args, **kwargs):
        return getattr(to, func_name)(*args, **kwargs)
    return types.MethodType(forwarded_method, from_)


def create_proxy_interface(from_, to, ignore_list=None, override_existing=False):
    """
    Copies the public interface of the destination object, excluding names in the ignore_list,
    and creates an identical interface in 'src', which forwards calls to dst.
    If 'override_existing' is False, then attributes already existing in 'src' will not be
    overridden.
    """
    if not ignore_list:
        ignore_list = []
    for attr_name in dir(to):
        if not attr_name.startswith('_') and not attr_name in ignore_list:
            if callable(getattr(to, attr_name)):
                if override_existing or not hasattr(from_, attr_name):
                    setattr(from_, attr_name, create_forwarded_method(from_, to, attr_name))

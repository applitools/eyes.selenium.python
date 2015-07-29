"""
Logs handling.
"""
import functools
import logging
import sys

_DEFAULT_EYES_LOGGER_NAME = 'eyes'
_DEFAULT_EYES_FORMATTER = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')


class _Logger(object):
    """
    Simple logger. Supports only info and debug.
    Args:
        (str) name: The logger name.
        (int) level: The log level (e.g., logging.DEBUG)
        (callable) handler_factory: a callable which creates a handler object. We use a factory
                                    since the actual creation of the handler should occur in open.
        (logging.Formatter) formatter: A custom formatter for the logs.
    """
    def __init__(self, name=__name__, level=logging.DEBUG, handler_factory=lambda: None,
                 formatter=None):
        self._name = name
        self._logger = None
        # Setting handler (a logger must have at least one handler attached to it)
        self._handler_factory = handler_factory
        self._handler = None
        self._formatter = formatter
        self._level = level

    def open(self):
        # Actually create the handler
        self._handler = self._handler_factory()
        if self._handler:
            self._handler.setLevel(self._level)
            # Getting the logger
            self._logger = logging.getLogger(self._name)
            self._logger.setLevel(self._level)
            # Setting formatter
            if self._formatter is not None:
                self._handler.setFormatter(self._formatter)
            self._logger.addHandler(self._handler)

    def close(self):
        if self._logger:
            self._handler.close()
            # If we don't remove the handler and a call to logging.getLogger(...) will be made with
            # the same name as the current logger, the handler will remain.
            self._logger.removeHandler(self._handler)
            self._logger = None
            self._handler = None

    def info(self, msg):
        if self._logger:
            self._logger.info(msg)

    def debug(self, msg):
        if self._logger:
            self._logger.debug(msg)


class StdoutLogger(_Logger):
    """
    A simple logger class for printing to STDOUT.
    """
    def __init__(self, name=_DEFAULT_EYES_LOGGER_NAME, level=logging.DEBUG):
        handler_factory = functools.partial(logging.StreamHandler, sys.stdout)
        super(StdoutLogger, self).__init__(name, level, handler_factory, _DEFAULT_EYES_FORMATTER)


class FileLogger(_Logger):
    """
    A simple logger class for outputting log messages to a file
    Args:
        (str) filename: The name of this file to which logs should be written.
        (str) mode: The mode in which the log file is opened ('a' for appending, 'w' for overwrite).
        (str) encoding: The encoding in which logs will be written to the file.
        (boolean) delay: If True, file will not be opened until the first log message is emitted.
        (str) name: The logger's name.
        (int) level: The log level (e.g., logging.DEBUG)
    """
    def __init__(self, filename="eyes.log", mode='a', encoding=None, delay=0,
                 name=_DEFAULT_EYES_LOGGER_NAME, level=logging.DEBUG):
        handler_factory = functools.partial(logging.FileHandler, filename, mode, encoding, delay)
        super(FileLogger, self).__init__(name, level, handler_factory, _DEFAULT_EYES_FORMATTER)


class NullLogger(_Logger):
    """
    A simple logger class which does nothing (log messages are ignored).
    """
    def __init__(self, name=_DEFAULT_EYES_LOGGER_NAME, level=logging.DEBUG):
        super(NullLogger, self).__init__(name, level)


# This will be set by the user.
_logger_to_use = None
# Holds the actual logger after open is called.
_logger = None


def set_logger(logger=None):
    global _logger_to_use
    _logger_to_use = logger


def open_():
    global _logger
    _logger = _logger_to_use
    if _logger is not None:
        _logger.open()


def close():
    global _logger
    if _logger is not None:
        _logger.close()
        _logger = None


def info(msg):
    if _logger is not None:
        _logger.info(msg)


def debug(msg):
    if _logger is not None:
        _logger.debug(msg)


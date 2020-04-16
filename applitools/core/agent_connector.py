from __future__ import absolute_import

import itertools
import math
import time
import typing as tp
import uuid
from datetime import datetime

import requests
from requests.packages import urllib3

from applitools.utils import general_utils
from applitools.utils.compat import urljoin, gzip_compress  # type: ignore
from . import logger, EyesError
from .test_results import TestResults
from ..utils.general_utils import UTC

if tp.TYPE_CHECKING:
    from typing import Dict, Optional, Text, Callable, Any
    from requests.models import Response
    from ..utils.custom_types import RunningSession, SessionStartInfo, Num

# Prints out all data sent/received through 'requests'
# import httplib
# httplib.HTTPConnection.debuglevel = 1

# Remove Unverified SSL warnings propagated by requests' internal urllib3 module
if hasattr(urllib3, "disable_warnings") and callable(urllib3.disable_warnings):
    urllib3.disable_warnings()


def _parse_response_with_json_data(response):
    # type: (Response) -> tp.Dict[tp.Text, tp.Any]
    response.raise_for_status()
    return response.json()


def to_rfc1123_datetime(dt):
    # type: (datetime) -> Text
    """Return a string representation of a date according to RFC 1123
    (HTTP/1.1).

    The supplied date must be in UTC.

    """
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
        weekday,
        dt.day,
        month,
        dt.year,
        dt.hour,
        dt.minute,
        dt.second,
    )


def current_time_in_rfc1123():
    # type: () -> Text
    return to_rfc1123_datetime(datetime.now(UTC))


def retry(delays=(0, 100, 500), exception=Exception, report=lambda *args: None):
    """
    This is a Python decorator which helps implementing an aspect oriented
    implementation of a retrying of certain steps which might fail sometimes.
    https://code.activestate.com/recipes/580745-retry-decorator-in-python/
    """

    def wrapper(function):
        def wrapped(*args, **kwargs):
            problems = []
            for delay in itertools.chain(delays, [None]):
                try:
                    return function(*args, **kwargs)
                except exception as problem:
                    problems.append(problem)
                    if delay is None:
                        report("retryable failed definitely: {}".format(problems))
                        raise
                    else:
                        report(
                            "retryable failed: {} -- delaying for {}".format(
                                problem, delay
                            )
                        )
                        time.sleep(delay)

        return wrapped

    return wrapper


class AgentConnector(object):
    """
    Provides an API for communication with the Applitools server.
    """

    _TIMEOUT = 60 * 5  # Seconds
    LONG_REQUEST_DELAY_MS = 2000  # type: int
    MAX_LONG_REQUEST_DELAY_MS = 10000  # type: int
    LONG_REQUEST_DELAY_MULTIPLICATIVE_INCREASE_FACTOR = 1.5  # type: float
    _DEFAULT_HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-applitools-eyes-client": None,
    }

    def __init__(self, server_url, full_agent_id):
        # type: (tp.Text, tp.Text) -> None
        """
        Ctor.

        :param server_url: The url of the Applitools server.
        """
        # Used inside the server_url property.
        self._server_url = None
        self._endpoint_uri = None
        self._render_info = None

        self.api_key = None  # type: ignore
        self.server_url = server_url
        self._DEFAULT_HEADERS['x-applitools-eyes-client'] = full_agent_id

    @property
    def server_url(self):
        # type: () -> tp.Text
        return self._server_url  # type: ignore

    @server_url.setter
    def server_url(self, server_url):
        # type: (tp.Text) -> None
        self._server_url = server_url  # type: ignore
        self._endpoint_uri = server_url.rstrip("/") + "/api/sessions/running"  # type: ignore

    def long_request(self, method, url, **kwargs):
        # type: (Callable, Text, **Any) -> Response
        headers = kwargs.get("headers", AgentConnector._DEFAULT_HEADERS).copy()
        headers["Eyes-Expect"] = "202+location"
        headers["Eyes-Date"] = current_time_in_rfc1123()
        kwargs["headers"] = headers
        response = method(url, **kwargs)
        logger.debug("Long request `{}` for {}".format(method.__name__, response.url))
        return self._long_request_check_status(response)

    def _long_request_check_status(self, response):
        if (
            response.status_code == requests.codes.ok
            or "Location" not in response.headers
        ):
            # request ends successful or it doesn't support Long request
            return response
        elif response.status_code == requests.codes.accepted:
            # long request here; calling received url to know that request was processed
            url = response.headers["Location"]
            response = self._long_request_loop(url)
            return self._long_request_check_status(response)
        elif response.status_code == requests.codes.created:
            # delete url that was used before
            url = response.headers["Location"]
            return requests.delete(
                url,
                headers={
                    "Eyes-Date": current_time_in_rfc1123(),
                    "x-applitools-eyes-client": self._DEFAULT_HEADERS['x-applitools-eyes-client']
                },
                verify=False,
                params=dict(apiKey=self.api_key),
            )
        elif response.status_code == requests.codes.gone:
            raise EyesError("The server task has gone.")
        else:
            raise EyesError("Unknown error during long request: {}".format(response))

    def _long_request_loop(self, url, delay=LONG_REQUEST_DELAY_MS):
        delay = min(
            self.MAX_LONG_REQUEST_DELAY_MS,
            math.floor(delay * self.LONG_REQUEST_DELAY_MULTIPLICATIVE_INCREASE_FACTOR),
        )
        logger.debug("Still running... Retrying in {} ms".format(delay))

        time.sleep(delay / 1000.0)
        response = requests.get(
            url,
            headers={
                "Eyes-Date": current_time_in_rfc1123(),
                "x-applitools-eyes-client": self._DEFAULT_HEADERS['x-applitools-eyes-client']
                },
            verify=False,
            params=dict(apiKey=self.api_key),
        )
        if response.status_code != requests.codes.ok:
            return response
        return self._long_request_loop(url, delay)

    def start_session(self, session_start_info):
        # type: (SessionStartInfo) -> RunningSession
        """
        Starts a new running session in the agent. Based on the given parameters,
        this running session will either be linked to an existing session, or to
        a completely new session.

        :param session_start_info: The start params for the session.
        :return: Represents the current running session.
        """
        data = '{"startInfo": %s}' % (general_utils.to_json(session_start_info))
        response = self.long_request(
            requests.post,
            self._endpoint_uri,
            data=data,
            verify=False,
            params=dict(apiKey=self.api_key),
            headers=AgentConnector._DEFAULT_HEADERS,
            timeout=AgentConnector._TIMEOUT,
        )
        parsed_response = _parse_response_with_json_data(response)
        return dict(
            session_id=parsed_response["id"],
            session_url=parsed_response["url"],
            is_new_session=parsed_response["isNew"],
        )

    def stop_session(self, running_session, is_aborted, save):
        # type: (RunningSession, bool, bool) -> TestResults
        """
        Stops a running session in the Eyes server.

        :param running_session: The session to stop.
        :param is_aborted: Whether the server should mark this session as aborted.
        :param save: Whether the session should be automatically saved if it is not aborted.
        :return: Test results of the stopped session.
        """
        logger.debug("Stop session called..")
        session_uri = "%s/%s" % (self._endpoint_uri, running_session["session_id"])
        params = {"aborted": is_aborted, "updateBaseline": save, "apiKey": self.api_key}
        response = self.long_request(
            requests.delete,
            session_uri,
            params=params,
            verify=False,
            headers=AgentConnector._DEFAULT_HEADERS,
            timeout=AgentConnector._TIMEOUT,
        )
        pr = _parse_response_with_json_data(response)
        logger.debug("stop_session(): parsed response: {}".format(pr))
        return TestResults(
            pr.get("steps"),
            pr.get("matches"),
            pr.get("mismatches"),
            pr.get("missing"),
            pr.get("exactMatches"),
            pr.get("strictMatches"),
            pr.get("contentMatches"),
            pr.get("layoutMatches"),
            pr.get("noneMatches"),
            pr.get("status"),
        )

    def render_info(self):
        # type: () -> Optional[Dict]
        logger.debug("render_info() called.")
        headers = AgentConnector._DEFAULT_HEADERS.copy()
        headers["Content-Type"] = "application/json"
        response = self.long_request(
            requests.get,
            url=urljoin(self._endpoint_uri, "/api/sessions/renderinfo"),
            params=dict(apiKey=self.api_key),
            verify=False,
            headers=headers,
            timeout=AgentConnector._TIMEOUT,
        )
        if not response.ok:
            raise EyesError(
                "Cannot get render info: \n Status: {}, Content: {}".format(
                    response.status_code, response.content
                )
            )
        self._render_info = response.json()
        return self._render_info

    def _try_upload_data(self, data_bytes, content_type, media_type):
        # type: (bytes, Text, Text) -> Optional[Text]
        rendering_info = self.render_info()

        if rendering_info and "resultsUrl" in rendering_info:
            try:
                target_url = rendering_info["resultsUrl"]
                guid = uuid.uuid4()
                target_url = target_url.replace("__random__", str(guid))
                logger.info("uploading image to {}".format(target_url))
                if self._upload_data(
                    data_bytes, rendering_info, target_url, content_type, media_type
                ):
                    return target_url
            except Exception as e:
                logger.debug("Error uploading image")
                logger.debug(str(e))

    @retry(delays=(0.5, 1, 10), exception=EyesError, report=logger.debug)
    def _upload_data(self, data_bytes, rendering_info, target_url, content_type, media_type):
        # type: (bytes, Dict, Text, Text, Text) -> bool
        headers = AgentConnector._DEFAULT_HEADERS.copy()
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(data_bytes))
        headers["Media-Type"] = media_type
        headers["X-Auth-Token"] = rendering_info["accessToken"]
        headers["x-ms-blob-type"] = "BlockBlob"

        response = requests.put(
            target_url,
            data=data_bytes,
            headers=headers,
            timeout=AgentConnector._TIMEOUT,
            verify=False,
        )
        if response.status_code in [requests.codes.ok, requests.codes.created]:
            logger.info("Upload Status Code: {}".format(response.status_code))
            return True
        raise EyesError(
            "Failed to Upload Data. Status Code: {}".format(response.status_code)
        )

    def match_window(self, running_session, data):
        # type: (RunningSession, tp.Text) -> bool
        """
        Matches the current window to the immediate expected window in the Eyes server. Notice that
        a window might be matched later at the end of the test, even if it was not immediately
        matched in this call.

        :param running_session: The current session that is running.
        :param data: The data for the requests.post.
        :return: The parsed response.
        """
        # logger.debug("Data length: %d, data: %s" % (len(data), repr(data)))
        session_uri = "%s/%s" % (self._endpoint_uri, running_session["session_id"])
        # Using the default headers, but modifying the "content type" to binary
        headers = AgentConnector._DEFAULT_HEADERS.copy()
        headers["Content-Type"] = "application/octet-stream"

        response = self.long_request(
            requests.post,
            session_uri,
            params=dict(apiKey=self.api_key),
            data=data,
            verify=False,
            headers=headers,
            timeout=AgentConnector._TIMEOUT,
        )
        parsed_response = _parse_response_with_json_data(response)
        return parsed_response["asExpected"]

    def post_dom_capture(self, dom_json):
        # type: (tp.Text) -> tp.Optional[tp.Text]
        """
        Upload the DOM of the tested page.
        Return an URL of uploaded resource which should be posted to AppOutput.
        """
        dom_bytes = gzip_compress(dom_json.encode("utf-8"))
        return self._try_upload_data(dom_bytes, "application/octet-stream", "application/json")

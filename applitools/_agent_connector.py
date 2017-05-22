import time
import requests
from requests.packages import urllib3
from applitools import logger
from .test_results import TestResults
from .utils import general_utils

## Prints out all data sent/received through 'requests'
# import httplib
# httplib.HTTPConnection.debuglevel = 1

# Remove Unverified SSL warnings propagated by requests' internal urllib3 module
if hasattr(urllib3, 'disable_warnings') and callable(urllib3.disable_warnings):
    urllib3.disable_warnings()


def _parse_response_with_json_data(response):
    response.raise_for_status()
    return response.json()


class AgentConnector(object):
    """
    Provides an API for communication with the Applitools server.
    """
    _TIMEOUT = 60 * 5  # Seconds
    _DEFAULT_HEADERS = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    def __init__(self, server_url):
        """
        Ctor.

        :param server_url: The url of the Applitools server.
        """
        # Used inside the server_url property.
        self._server_url = None
        self._endpoint_uri = None

        self.api_key = None
        self.server_url = server_url

    @property
    def server_url(self):
        return self._server_url

    @server_url.setter
    def server_url(self, server_url):
        self._server_url = server_url
        self._endpoint_uri = server_url.rstrip('/') + '/api/sessions/running'

    @staticmethod
    def _send_long_request(name, method, *args, **kwargs):
        delay = 2  # Seconds
        headers = kwargs['headers'].copy()
        headers['Eyes-Expect'] = '202-accepted'
        while True:
            # Sending the current time of the request (in RFC 1123 format)
            headers['Eyes-Date'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
            kwargs['headers'] = headers
            response = method(*args, **kwargs)
            if response.status_code != 202:
                return response
            logger.debug("{0}: Still running... Retrying in {1}s".format(name, delay))
            time.sleep(delay)
            delay = min(10, delay * 1.5)

    def start_session(self, session_start_info):
        """
        Starts a new running session in the agent. Based on the given parameters,
        this running session will either be linked to an existing session, or to
        a completely new session.

        :param session_start_info: The start params for the session.
        :return: Represents the current running session.
        """
        data = '{"startInfo": %s}' % (general_utils.to_json(session_start_info))
        response = requests.post(self._endpoint_uri, data=data, verify=False, params=dict(apiKey=self.api_key),
                                 headers=AgentConnector._DEFAULT_HEADERS,
                                 timeout=AgentConnector._TIMEOUT)
        parsed_response = _parse_response_with_json_data(response)
        return dict(session_id=parsed_response['id'], session_url=parsed_response['url'],
                    is_new_session=(response.status_code == requests.codes.created))

    def stop_session(self, running_session, is_aborted, save):
        """
        Stops a running session in the Eyes server.

        :param running_session: The session to stop.
        :param is_aborted: Whether the server should mark this session as aborted.
        :param save: Whether the session should be automatically saved if it is not aborted.
        :return: Test results of the stopped session.
        """
        logger.debug('Stop session called..')
        session_uri = "%s/%s" % (self._endpoint_uri, running_session['session_id'])
        params = {'aborted': is_aborted, 'updateBaseline': save, 'apiKey': self.api_key}
        response = AgentConnector._send_long_request("stop_session", requests.delete, session_uri,
                                                     params=params, verify=False,
                                                     headers=AgentConnector._DEFAULT_HEADERS,
                                                     timeout=AgentConnector._TIMEOUT)
        pr = _parse_response_with_json_data(response)
        return TestResults(pr['steps'], pr['matches'], pr['mismatches'], pr['missing'],
                           pr['exactMatches'], pr['strictMatches'], pr['contentMatches'],
                           pr['layoutMatches'], pr['noneMatches'])

    def match_window(self, running_session, data):
        """
        Matches the current window to the immediate expected window in the Eyes server. Notice that
        a window might be matched later at the end of the test, even if it was not immediately
        matched in this call.

        :param running_session: The current session that is running.
        :param data: The data for the requests.post.
        :return: The parsed response.
        """
        # logger.debug("Data length: %d, data: %s" % (len(data), repr(data)))
        session_uri = "%s/%s" % (self._endpoint_uri, running_session['session_id'])
        # Using the default headers, but modifying the "content type" to binary
        headers = AgentConnector._DEFAULT_HEADERS.copy()
        headers['Content-Type'] = 'application/octet-stream'
        response = requests.post(session_uri, params=dict(apiKey=self.api_key), data=data, verify=False,
                                 headers=headers, timeout=AgentConnector._TIMEOUT)
        parsed_response = _parse_response_with_json_data(response)
        return parsed_response['asExpected']

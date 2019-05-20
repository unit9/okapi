import logging
import re

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import os
import requests

from . import exceptions as api_client_exceptions

logger = logging.getLogger('HTTP Transport')
logging.basicConfig(level=logging.DEBUG)

# ===================== Google App Engine Support =============================
# if run in Py 2 GAE env, including dev_appserver, do necessary hacks
server_software = os.getenv('SERVER_SOFTWARE')
logger.debug(server_software)
if server_software:
    logger.debug('APPENGINE_RUNTIME ' + os.getenv('APPENGINE_RUNTIME'))
    if 'python27' in os.getenv('APPENGINE_RUNTIME'):
        logger.debug('is py2.7 runtime')
        from requests_toolbelt.adapters import appengine
        appengine.monkeypatch()


class HTTPSession(requests.Session):
    # Used in pagination, might be very specific per-server.
    # Pagination info can also be present in the response instead of header.
    # (in the header should be the way).
    # override this as you wish
    LINKS_HEADER_NAME = 'Link'

    auth_header_name = 'Authorization'

    def __init__(self, host, auth_header_name=None, api_key=None,
                 *args, **kwargs):
        # original imple has no args
        super(HTTPSession, self).__init__()

        if auth_header_name is not None and api_key is not None:
            self.auth_header_name = auth_header_name
            self.headers.update({
                self.auth_header_name: api_key
            })

        self.host = host

    def get_next_url(self, headers):
        """
        Assuming server has Links/links header name.
        Might be very specific.
        Override the class attribute if you wish
        """
        try:
            links = requests.utils.parse_header_links(
                headers[self.LINKS_HEADER_NAME].rstrip('>').replace('>,<', ',<')
            )
        except KeyError:
            return None

        next_url = None
        for link in links:
            if link['rel'] == 'next':
                next_url = link['url'] if link['url'] else None

        return next_url

    def _request(self, method, url, json=None, result=None, paginate=False,
                 data=None):
        """Core transport layer"""
        if json is not None:
            resp = self.request(method, url, json=json)
        else:
            resp = self.request(method, url, data=data)

        pagination_log = '(PAGINATED) ' if paginate else ''
        # TODO implement verbosity
        # logged by urllib
        # logger.debug('{}Made request to '.format(pagination_log) + url)
        # logger.debug('{}Response is '.format(pagination_log) + str(resp))
        # logger.debug('{}Response headers are '.format(pagination_log) + str(resp.headers))  # noqa
        if resp.status_code >= 400:
            self.handle_error_response(resp)

        # pagination
        if method == 'GET' and paginate:
            next_url = self.get_next_url(resp.headers)
            if next_url:
                if result is None:
                    result = resp.json()
                else:
                    result += resp.json()
                self._request('GET', next_url, result=result, paginate=True)
            else:
                # if only has one page
                if result is None:
                    result = resp.json()
                else:
                    result += resp.json()
        else:
            result = resp.json()

        # logger.debug('{}Response content is '.format(pagination_log) + str(result))  # noqa
        return result

    @staticmethod
    def handle_error_response(response):
        # Generalized mapping of API response codes to exception classes
        # Good to have more specific implementation in the APIClient
        status_codes = {
            4: api_client_exceptions.InvalidParamsError,
            5: api_client_exceptions.GeneralInternalHostError,
        }

        for status_code, exception in status_codes.items():
            if str(response.status_code)[0] == str(status_code):
                break

        try:
            data = response.json()
        except Exception:
            data = response.content

        message = {'url': response.url, 'data': data}

        raise exception(
            response=response,
            code=response.status_code,
            data=data,
            message=message
        )


class Resource(object):
    path = None

    def __init__(self, api_client):
        self.api_client = api_client

        if self.path is None:
            # turns into "standard" REST resource paths
            self.path = re.sub(
                r"(\w)([A-Z])", r"\1-\2", self.__class__.__name__
            ).lower().replace('_', '-') + 's'

    @property
    def url(self):
        return self.api_client.url + self.path

    def construct_url(self, *args):
        """
        Used for creating URLs with self.URL as the base.
        Just a fancy way of joining args with '/'
        :param args:
        :return:
        """
        path = '/'.join(args)
        return self.url + '/' + path

    # TODO implement customizable methods for caching
    # @lrudecorator(512)
    def get(self, *args, **kwargs):
        """put URL query as kwargs"""
        url_queries = urlencode(kwargs)
        identifier = str(args[0])
        data = self.api_client.session._request(
            method='GET', url=self.construct_url(identifier) + '?' + url_queries  # noqa
        )
        return data

    def list(self, paginate=False, *args, **kwargs):
        url_queries = urlencode(kwargs)
        data = self.api_client.session._request(
            method='GET', url=self.url + '?' + url_queries, paginate=paginate
        )
        return data

    def create(self):
        raise NotImplementedError

    def delete(self, identifier):
        raise NotImplementedError


class APIClient(object):
    resources = []

    def __getattr__(self, item):
        # allow resource instantiation on the fly
        _Resource = type(item, (Resource,), {})
        resource = _Resource(self)
        setattr(self, item, resource)
        return resource

    def __init__(self, host, api_key=None, version='v1',
                 auth_header_name=None):
        self.host = host
        self.version = version
        self.session = HTTPSession(
            auth_header_name=auth_header_name,
            api_key=api_key,
            host=host
        )

        for resource in self.resources:
            attr_name = re.sub(
                r"(\w)([A-Z])", r"\1_\2", resource.__name__
            ).lower()
            setattr(self, attr_name, resource(api_client=self))

    @property
    def url(self):
        # refactor version so that the argument is only the number
        # e.g. 1 opposed to v1?
        return '{}/{}/'.format(self.host, self.version)

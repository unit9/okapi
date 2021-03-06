import json
import logging
import re

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import os
import requests

from . import exceptions as api_client_exceptions

http_logger = logging.getLogger('HTTP Transport')
okapi_logger = logging.getLogger('okapi')

# ===================== Google App Engine Support =============================
# if run in Py 2 GAE env, including dev_appserver, do necessary hacks
server_software = os.getenv('SERVER_SOFTWARE', 'ENV_VAR_NOT_EXIST')
okapi_logger.debug('SERVER_SOFTWARE: ' + server_software)
if server_software:
    okapi_logger.debug('APPENGINE_RUNTIME: ' + os.getenv('APPENGINE_RUNTIME', 'ENV_VAR_NOT_EXIST'))  # noqa
    if 'python27' in os.getenv('GAE_RUNTIME', 'ENV_VAR_NOT_EXIST'):
        okapi_logger.debug('is py2.7 runtime')
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
                 data=None, **kwargs):
        """
        Core transport layer

        Returns response object if paginate is False, else returns
        concanated response.json()
        """
        if json is not None:
            resp = self.request(method, url, json=json, **kwargs)
        else:
            resp = self.request(method, url, data=data, **kwargs)

        pagination_log = '(PAGINATED) ' if paginate else ''
        # TODO implement verbosity
        # logged by urllib
        # http_logger.debug('{}Made request to '.format(pagination_log) + url)
        # http_logger.debug('{}Response is '.format(pagination_log) + str(resp))
        # http_logger.debug('{}Response headers are '.format(pagination_log) + str(resp.headers))  # noqa
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
            result = resp

        # http_logger.debug('{}Response content is '.format(pagination_log) + str(result))  # noqa
        return result

    @staticmethod
    def handle_error_response(response):
        # Generalized mapping of API response codes to exception classes
        # Good to have more specific implementation in the APIClient
        status_codes = {
            4: api_client_exceptions.BadRequestError,
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

    def __getattr__(self, item):
        # allow non-ended resource URLs
        _Resource = type(item, (Resource,), {})
        resource = _Resource(self.api_client, self)
        setattr(self, item, resource)
        return resource

    def __init__(self, api_client, parent_resource=None):
        self.api_client = api_client
        self.parent_resource = parent_resource

        if self.path is None:
            # turns into "standard" REST resource paths (without plural s)
            self.path = re.sub(
                r"(\w)([A-Z])", r"\1-\2", self.__class__.__name__
            ).lower().replace('_', '-')

    @property
    def url(self):
        return self.api_client.url + self._path

    @property
    def _path(self):
        return (
            self.path if not self.parent_resource
            else self.parent_resource._path + '/' + self.path
        )

    def construct_url(self, *args):
        """
        Used for creating URLs with self.URL as the base.
        Just a fancy way of joining args with '/'
        :param args:
        :return:
        """
        path = '/'.join([str(e) for e in args])
        return self.url + '/' + path

    def get(self, identifier, forced_url='', request_kwargs=None, *args, **kwargs):
        if request_kwargs is None:
            request_kwargs = {}

        if not forced_url:
            url_queries = urlencode(kwargs)
            url = self.construct_url(identifier) + '?' + url_queries
        else:
            url = self.api_client.url + forced_url

        data = self.api_client.session._request(
            method='GET',
            url=url,
            **request_kwargs
        )
        return data

    def list(self, paginate=False, forced_url='', request_kwargs=None, *args, **kwargs):
        """
        When paginate is True, return concanated data else return response obj
        """
        if request_kwargs is None:
            request_kwargs = {}

        if not forced_url:
            url_queries = urlencode(kwargs)
            url = self.url + '?' + url_queries
        else:
            url = self.api_client.url + forced_url

        return self.api_client.session._request(
            method='GET',
            url=url,
            paginate=paginate,
            **request_kwargs
        )

    def create(self, data, forced_url='', request_kwargs=None, *args, **kwargs):
        if request_kwargs is None:
            request_kwargs = {}

        if not forced_url:
            url_queries = urlencode(kwargs)
            url = self.url + '?' + url_queries
        else:
            url = self.api_client.url + forced_url

        return self.api_client.session._request(
            method='POST',
            url=url,
            json=data,
            **request_kwargs
        )

    def update(self, identifier, data, forced_url='', request_kwargs=None, *args, **kwargs):
        if request_kwargs is None:
            request_kwargs = {}

        if not forced_url:
            url_queries = urlencode(kwargs)
            url = self.construct_url(identifier) + '?' + url_queries
        else:
            url = self.api_client.url + forced_url

        return self.api_client.session._request(
            method='PUT',
            url=url,
            json=data,
            **request_kwargs
        )

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

        # if resources class attribute is set
        for resource in self.resources:
            attr_name = re.sub(
                r"(\w)([A-Z])", r"\1_\2", resource.__name__
            ).lower()
            setattr(self, attr_name, resource(api_client=self))

    # FIXME should be URI since it has no scheme
    @property
    def url(self):
        # refactor version so that the argument is only the number
        # e.g. 1 opposed to v1?
        return (
            '{}/{}/'.format(self.host, self.version)
            if self.version
            else self.host + '/'
        )

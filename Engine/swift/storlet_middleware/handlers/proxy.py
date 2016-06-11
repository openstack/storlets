# Copyright (c) 2010-2015 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from six.moves.urllib.parse import quote
from swift.common.constraints import check_copy_from_header, \
    check_destination_header
from swift.common.swob import HTTPBadRequest, HTTPUnauthorized, \
    HTTPMethodNotAllowed, HTTPPreconditionFailed
from swift.common.utils import config_true_value, public
from swift.common.wsgi import make_subrequest
from swift.proxy.controllers.base import get_account_info
from storlet_middleware.handlers.base import StorletBaseHandler, \
    NotStorletRequest, NotStorletExecution


CONDITIONAL_KEYS = ['IF_MATCH', 'IF_NONE_MATCH', 'IF_MODIFIED_SINCE',
                    'IF_UNMODIFIED_SINCE']


class StorletProxyHandler(StorletBaseHandler):
    def __init__(self, request, conf, app, logger):
        super(StorletProxyHandler, self).__init__(
            request, conf, app, logger)
        self.storlet_container = conf.get('storlet_container')
        self.storlet_dependency = conf.get('storlet_dependency')
        self.storlet_containers = [self.storlet_container,
                                   self.storlet_dependency]

        if not self.is_storlet_request:
            # This is not storlet-related request, so pass it
            raise NotStorletRequest()

        # In proxy server, storlet handler validate if storlet enabled
        # at the account, anyway
        account_meta = get_account_info(self.request.environ,
                                        self.app)['meta']
        storlets_enabled = account_meta.get('storlet-enabled',
                                            'False')
        if not config_true_value(storlets_enabled):
            self.logger.debug('Account disabled for storlets')
            raise HTTPBadRequest('Account disabled for storlets',
                                 request=self.request)

        if self.is_storlet_object_update:
            # TODO(takashi): We have to validate metadata in COPY case
            self._validate_registration(self.request)
            raise NotStorletExecution()
        else:
            # if self.is_storlet_execution
            self._setup_gateway()

    def _parse_vaco(self):
        return self.request.split_path(4, 4, rest_with_last=True)

    def is_proxy_runnable(self, resp):
        """
        Check if the storlet should be executed at proxy server

        :param resp: swob.Response instance
        :return: Whether we should execute the storlet at proxy
        """
        # SLO / proxy only case:
        # storlet to be invoked now at proxy side:
        runnable = any(
            [self.is_storlet_range_request, self.is_slo_response(resp),
             self.conf['storlet_execute_on_proxy_only']])
        return runnable

    @property
    def is_storlet_request(self):
        return self.is_storlet_execution or self.is_storlet_object_update

    @property
    def is_storlet_object_update(self):
        return (self.container in self.storlet_containers and self.obj
                and self.request.method in ['PUT', 'POST'])

    @property
    def is_put_copy_request(self):
        return 'X-Copy-From' in self.request.headers

    def _parse_storlet_params(self, headers):
        """
        Parse storlet parameters from storlet/dependency object metadata

        :returns: dict of storlet parameters
        """
        params = dict()
        for key in headers:
            if key.startswith('X-Object-Meta-Storlet'):
                params[key[len('X-Object-Meta-Storlet-'):]] = headers[key]
        return params

    def _validate_registration(self, req):
        """
        Validate parameters about storlet/dependency object when registrating

        :params req: swob.Request instance
        :raises ValueError: If some parameters are wrong
        """
        params = self._parse_storlet_params(req.headers)
        try:
            if self.container == self.storlet_container:
                self.logger.debug('updating object in storlet container. '
                                  'Sanity check')
                self.gateway_class.validate_storlet_registration(
                    params, self.obj)
            else:
                self.logger.debug('updating object in storlet dependency. '
                                  'Sanity check')
                self.gateway_class.validate_dependency_registration(
                    params, self.obj)
        except ValueError as e:
            self.logger.exception('Bad parameter')
            raise HTTPBadRequest(e.message)

    def verify_access_to_storlet(self):
        """
        Verify access to the storlet object

        :return: storlet parameters
        :raises HTTPUnauthorized: If it fails to verify access
        """
        sobj = self.request.headers.get('X-Run-Storlet')
        spath = '/'.join(['', self.api_version, self.account,
                          self.storlet_container, sobj])
        self.logger.debug('Verify access to %s' % spath)

        new_env = dict(self.request.environ)
        if 'HTTP_TRANSFER_ENCODING' in new_env.keys():
            del new_env['HTTP_TRANSFER_ENCODING']

        for key in CONDITIONAL_KEYS:
            env_key = 'HTTP_' + key
            if env_key in new_env.keys():
                del new_env[env_key]

        auth_token = self.request.headers.get('X-Auth-Token')
        storlet_req = make_subrequest(
            new_env, 'HEAD', spath,
            headers={'X-Auth-Token': auth_token},
            swift_source='SE')

        resp = storlet_req.get_response(self.app)
        if not resp.is_success:
            raise HTTPUnauthorized('Failed to verify access to the storlet',
                                   request=self.request)

        params = self._parse_storlet_params(resp.headers)
        for key in ['Content-Length', 'X-Timestamp']:
            params[key] = resp.headers[key]
        return params

    def handle_request(self):
        if hasattr(self, self.request.method):
            try:
                handler = getattr(self, self.request.method)
                getattr(handler, 'publicly_accessible')
            except AttributeError:
                # TODO(kota_): add allowed_method list to Allow header
                return HTTPMethodNotAllowed(request=self.request)
            return handler()
        else:
            raise HTTPMethodNotAllowed(request=self.request)

    def _call_gateway(self, resp):
        return self.gateway.gatewayProxyGetFlow(self.request, resp)

    def augment_storlet_request(self, params):
        """
        Add to request the storlet parameters to be used in case the request
        is forwarded to the data node (GET case)

        :param params: paramegers to be augmented to request
        """
        for key, val in params.iteritems():
            self.request.headers['X-Storlet-' + key] = val

    @public
    def GET(self):
        """
        GET handler on Proxy
        """
        if self.is_range_request:
            raise HTTPBadRequest('Storlet execution with range header is not'
                                 ' supported', request=self.request)

        params = self.verify_access_to_storlet()
        self.augment_storlet_request(params)

        if self.is_storlet_range_request:
            self.request.headers['Range'] = \
                self.request.headers['X-Storlet-Range']

        original_resp = self.request.get_response(self.app)

        if original_resp.is_success:
            # The get request may be a SLO object GET request.
            # Simplest solution would be to invoke a HEAD
            # for every GET request to test if we are in SLO case.
            # In order to save the HEAD overhead we implemented
            # a slightly more involved flow:
            # At proxy side, we augment request with Storlet stuff
            # and let the request flow.
            # At object side, we invoke the plain (non Storlet)
            # request and test if we are in SLO case.
            # and invoke Storlet only if non SLO case.
            # Back at proxy side, we test if test received
            # full object to detect if we are in SLO case,
            # and invoke Storlet only if in SLO case.
            if self.is_proxy_runnable(original_resp):
                return self.apply_storlet(original_resp)
            else:
                # Non proxy GET case: Storlet was already invoked at
                # object side
                # TODO(kota_): Do we need to pop the Transfer-Encoding/
                #              Content-Length header from the resp?
                if 'Transfer-Encoding' in original_resp.headers:
                    original_resp.headers.pop('Transfer-Encoding')

                original_resp.headers['Content-Length'] = None
                return original_resp

        else:
            # In failure case, we need nothing to do, just return original
            # response
            return original_resp

    def _validate_copy_request(self):
        # We currently block copy from account
        unsupported_headers = ['X-Copy-From-Account',
                               'Destination-Account',
                               'X-Fresh-Metadata']

        for header in unsupported_headers:
            if self.request.headers.get(header):
                raise HTTPBadRequest(
                    'Storlet on copy with %s is not supported' %
                    header)

    def handle_put_copy_response(self, out_md, app_iter):
        self.request.environ['wsgi.input'] = app_iter
        if 'CONTENT_LENGTH' in self.request.environ:
            self.request.environ.pop('CONTENT_LENGTH')
        self.request.headers['Transfer-Encoding'] = 'chunked'
        return self.request.get_response(self.app)

    def base_handle_copy_request(self, src_container, src_obj,
                                 dest_container, dest_object):
        """
        Unified path for:
        PUT verb with X-Copy-From and
        COPY verb with Destination
        """
        # Get an iterator over the source object
        source_path = '/%s/%s/%s/%s' % (self.api_version, self.account,
                                        src_container, src_obj)
        source_req = self.request.copy_get()
        source_req.headers.pop('X-Backend-Storage-Policy-Index', None)
        source_req.headers.pop('X-Run-Storlet', None)
        source_req.path_info = source_path
        source_req.headers['X-Newest'] = 'true'

        source_resp = source_req.get_response(self.app)

        # Do proxy copy flow
        (out_md, app_iter) = self.gateway.gatewayProxyCopyFlow(self.request,
                                                               source_resp)

        resp = self.handle_put_copy_response(out_md, app_iter)
        acct, path = source_resp.environ['PATH_INFO'].split('/', 3)[2:4]
        resp.headers['X-Storlet-Generated-From-Account'] = quote(acct)
        resp.headers['X-Storlet-Generated-From'] = quote(path)
        if 'last-modified' in source_resp.headers:
            resp.headers['X-Storlet-Generated-From-Last-Modified'] = \
                source_resp.headers['last-modified']
        return resp

    @public
    def PUT(self):
        """
        PUT handler on Proxy
        """

        params = self.verify_access_to_storlet()
        self.augment_storlet_request(params)
        if self.is_put_copy_request:
            self. _validate_copy_request()
            src_container, src_obj = check_copy_from_header(self.request)
            dest_container = self.container
            dest_object = self.obj
            self.request.headers.pop('X-Copy-From', None)
            return self.base_handle_copy_request(src_container, src_obj,
                                                 dest_container, dest_object)

        (out_md, app_iter) = \
            self.gateway.gatewayProxyPutFlow(self.request)
        return self.handle_put_copy_response(out_md, app_iter)

    @public
    def COPY(self):
        """
        COPY handler on Proxy
        """
        if not self.request.headers.get('Destination'):
            return HTTPPreconditionFailed(request=self.request,
                                          body='Destination header required')

        params = self.verify_access_to_storlet()
        self.augment_storlet_request(params)
        self._validate_copy_request()
        dest_container, dest_object = check_destination_header(self.request)

        # re-write the existing request as a PUT instead of creating a new one
        # TODO(eranr): do we want a new sub_request or re-write existing one as
        # we do below. See proxy obj controller COPY.
        self.request.method = 'PUT'
        self.request.path_info = '/v1/%s/%s/%s' % \
                                 (self.account, dest_container, dest_object)
        self.request.headers['Content-Length'] = 0
        del self.request.headers['Destination']

        return self.base_handle_copy_request(self.container, self.obj,
                                             dest_container, dest_object)

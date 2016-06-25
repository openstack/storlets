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

from swift.common.swob import HTTPMethodNotAllowed, \
    HTTPRequestedRangeNotSatisfiable
from swift.common.utils import public
from storlet_middleware.handlers.base import StorletBaseHandler, \
    NotStorletRequest


class StorletObjectHandler(StorletBaseHandler):
    def __init__(self, request, conf, app, logger):
        super(StorletObjectHandler, self).__init__(
            request, conf, app, logger)
        # object need the gateway module only execution
        if (self.is_storlet_execution):
            self._setup_gateway()
        else:
            raise NotStorletRequest()

    def _parse_vaco(self):
        _, _, acc, cont, obj = self.request.split_path(
            5, 5, rest_with_last=True)
        # TODO(kota_): make sure why object server api version is 0?
        return ('0', acc, cont, obj)

    @property
    def is_slo_get_request(self):
        """
        Determines from a GET request and its  associated response
        if the object is a SLO
        """
        return self.request.params.get('multipart-manifest') == 'get'

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
            # un-defined method should be NOT ALLOWED
            raise HTTPMethodNotAllowed(request=self.request)

    def _call_gateway(self, resp):
        return self.gateway.gatewayObjectGetFlow(
            self.request, resp)

    @public
    def GET(self):
        """
        GET handler on object-server
        """
        self.logger.debug('GET. Run storlet')

        if self.is_range_request and not self.is_storlet_range_request:
            raise HTTPRequestedRangeNotSatisfiable(
                'Storlet execution with range header is not supported',
                request=self.request)

        orig_resp = self.request.get_response(self.app)

        if not orig_resp.is_success:
            return orig_resp

        # TODO(takashi): not sure manifest file should not be run with storlet
        not_runnable = any(
            [self.is_storlet_range_request, self.is_slo_get_request,
             self.conf['storlet_execute_on_proxy_only'],
             self.is_slo_response(orig_resp),
             self.has_run_on_proxy_header])

        if not_runnable:
            # Storlet must be invoked on proxy as it is:
            # either an SLO
            # or storlet-range-request
            # or proxy only mode
            self.logger.debug('storlet_handler: invocation '
                              'over %s/%s/%s %s' %
                              (self.account, self.container, self.obj,
                               'to be executed on proxy'))
            return orig_resp
        else:
            # We apply here the Storlet:
            self.logger.debug('storlet_handler: invocation '
                              'over %s/%s/%s %s' %
                              (self.account, self.container, self.obj,
                               'to be executed locally'))
            return self.apply_storlet(orig_resp)

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
    HTTPRequestedRangeNotSatisfiable, Range
from swift.common.utils import public
from storlets.swift_middleware.handlers.base import StorletBaseHandler, \
    NotStorletRequest


class StorletObjectHandler(StorletBaseHandler):
    def __init__(self, request, conf, gateway_conf, app, logger):
        super(StorletObjectHandler, self).__init__(
            request, conf, gateway_conf, app, logger)
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

    def _get_storlet_invocation_options(self, req):
        options = super(StorletObjectHandler, self).\
            _get_storlet_invocation_options(req)

        # If the request is a storlet request with an simgle input range, we
        # pass range parameters to storlet gateway, to realize range handling
        # with keepling zero copy
        if self.is_storlet_range_request and \
                not self.is_storlet_multiple_range_request:
            srange = Range(req.headers['X-Storlet-Range'])

            # As we should include the end byte in HTTP Range, here we +1
            # for the end cursor so that we can treat it as general range
            # (include start, and exclude end)
            options['range_start'] = srange.ranges[0][0]
            options['range_end'] = srange.ranges[0][1] + 1

        return options

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
        sreq = self._build_storlet_request(
            self.request, resp.headers, resp.app_iter)
        return self.gateway.invocation_flow(sreq)

    @public
    def GET(self):
        """
        GET handler on object-server
        """
        # The proxy may add a Range header in the case
        # where the execution is to be done on proxy only
        # (and X-Storlet-Range header exists)
        # Hence we allow having a Range header ONLY
        # if there is also X-Storlet-Range
        # Otherwise, running a Storlet together with
        # The HTTP Range header is not allowed
        if self.is_range_request and not self.is_storlet_range_request:
            raise HTTPRequestedRangeNotSatisfiable(
                b'Storlet execution with range header is not supported',
                request=self.request)

        orig_resp = self.request.get_response(self.app)

        if not orig_resp.is_success:
            return orig_resp

        # TODO(takashi): not sure manifest file should not be run with storlet
        not_runnable = any(
            [self.execute_on_proxy,
             self.execute_range_on_proxy,
             self.is_slo_get_request,
             self.is_slo_response(orig_resp)])

        if not_runnable:
            # Storlet must be invoked on proxy as it is:
            # either an SLO
            # or storlet-range-request
            # or proxy only mode
            self.logger.debug(
                'storlet_handler: invocation over %s to be executed on proxy'
                % self.request.path)
            return orig_resp
        else:
            # We apply here the Storlet:
            self.logger.debug(
                'storlet_handler: invocation over %s to be executed locally'
                % self.request.path)
            return self.apply_storlet(orig_resp)

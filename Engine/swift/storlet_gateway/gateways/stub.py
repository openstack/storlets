'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''
from six import BytesIO
from storlet_gateway.gateways.base import StorletGatewayBase


class StorletGatewayStub(StorletGatewayBase):

    def __init__(self, sconf, logger, app, account):
        self.logger = logger
        self.app = app
        self.account = account
        self.sconf = sconf

    @classmethod
    def validate_storlet_registration(cls, params, obj):
        pass

    @classmethod
    def validate_dependency_registration(cls, params, obj):
        pass

    def indentity_invocation(self, headers, body):
        self.logger.debug("Identity invocation is called")
        return headers, BytesIO(body)

    def augmentStorletRequest(self, request, headers):
        pass

    def gatewayProxyPutFlow(self, orig_request):
        return self.indentity_invocation(orig_request.headers,
                                         orig_request.body)

    def gatewayProxyCopyFlow(self, orig_request, source_resp):
        return self.indentity_invocation(source_resp.headers,
                                         source_resp.body)

    def gatewayProxyGetFlow(self, request, original_response):
        return self.indentity_invocation(original_response.headers,
                                         original_response.body)

    def gatewayObjectGetFlow(self, request, original_response):
        return self.indentity_invocation(original_response.headers,
                                         original_response.body)

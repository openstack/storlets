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
from storlet_gateway.storlet_base_gateway import StorletGatewayBase


class StorletGatewayStub(StorletGatewayBase):

    def __init__(self, storlet_conf, logger, app, version, account,
                 container, obj):
        self.logger = logger
        self.app = app
        self.version = version
        self.account = account
        self.container = container
        self.obj = obj
        self.storlet_conf = storlet_conf
        self.dummy_content = self.storlet_conf.get('dummy_content',
                                                   'DUMMY_CONTENT')

    def validateStorletUpload(self, req):
        self.logger.debug("Storlet request validated")
        return True

    def authorizeStorletExecution(self, req):
        self.logger.debug("Storlet execution is authorized")
        return True

    def dummy_invocation(self):
        self.logger.debug("Dummy invocation is called")
        return {}, [self.dummy_content]

    def augmentStorletRequest(self, request):
        pass

    def gatewayProxyPutFlow(self, orig_request, container, obj):
        return self.dummy_invocation()

    def gatewayProxySloFlow(self, request, container, obj, original_response):
        return self.dummy_invocation()

    def gatewayObjectGetFlow(self, request, container, obj, original_response):
        return self.dummy_invocation()

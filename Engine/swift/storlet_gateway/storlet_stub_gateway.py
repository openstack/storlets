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


class StorletStubBase(object):

    def __init__(self, storlet_conf, logger, app, version, account,
                 container, obj):
        self.logger = logger
        self.app = app
        self.version = version
        self.account = account
        self.container = container
        self.obj = obj
        self.storlet_conf = storlet_conf
        self.storlet_metadata = None
        self.storlet_timeout = int(self.storlet_conf['storlet_timeout'])

    def validateStorletUpload(self, req):
        self.logger.debug("Storlet request validated")
        return True

    def authorizeStorletExecution(self, req):
        self.logger.debug("Storlet execution is authorized")
        return True

    def augmentStorletRequest(self, req):
        self.logger.debug("Storlet request augmeneted")

    def gatewayProxyPutFlow(self, sreq, container, obj):
        raise NotImplementedError("Not implemented gatewayProxyPutFlow")

    def gatewayProxyGETFlow(self, req, container, obj, orig_resp):
        raise NotImplementedError("Not implemented gatewayProxyGETFlow")

    def gatewayObjectGetFlow(self, req, sreq, container, obj):
        raise NotImplementedError("Not implemented gatewayObjectGetFlow")

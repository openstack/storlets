"""-------------------------------------------------------------------------
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
-------------------------------------------------------------------------"""


class StorletGatewayBase(object):

    def validateStorletUpload(self, request):
        raise NotImplementedError("Not implemented: validateStorletUpload")

    def authorizeStorletExecution(self, request):
        raise NotImplementedError("Not implemented: authorizeStorletExecution")

    def augmentStorletRequest(self, request):
        raise NotImplementedError("Not implemented: augmentStorletRequest")

    def gatewayProxyPutFlow(self, orig_request, container, obj):
        raise NotImplementedError("Not implemented: gatewayProxyPutFlow")

    def gatewayProxyGetFlow(self, request, container, obj, original_response):
        raise NotImplementedError("Not implemented: gatewayProxySloFlow")

    def gatewayObjectGetFlow(self, request, container, obj, original_response):
        raise NotImplementedError("Not implemented: gatewayObjectGetFlow")

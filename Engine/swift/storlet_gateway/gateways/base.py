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
from storlet_gateway.common.stob import StorletRequest


class StorletGatewayBase(object):

    request_class = StorletRequest

    def __init__(self, sconf, logger, scope):
        self.logger = logger
        self.sconf = sconf
        self.scope = scope

    @classmethod
    def validate_storlet_registration(cls, params, obj):
        raise NotImplementedError("Not implemented: "
                                  "validate_storlet_registration")

    @classmethod
    def validate_dependency_registration(cls, params, obj):
        raise NotImplementedError("Not implemented: "
                                  "validate_dependency_registration")

    def invocation_flow(self, sreq):
        raise NotImplementedError("Not implemented: invocation_flow")

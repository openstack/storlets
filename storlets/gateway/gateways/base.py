# Copyright IBM Corp. 2015, 2015 All Rights Reserved
# Copyright (c) 2010-2016 OpenStack Foundation
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

import abc

from storlets.gateway.common.stob import StorletRequest


class StorletGatewayBase(object, metaclass=abc.ABCMeta):

    request_class = StorletRequest

    def __init__(self, conf, logger, scope):
        self.logger = logger
        self.conf = conf
        self.scope = scope

    @classmethod
    @abc.abstractmethod
    def validate_storlet_registration(cls, params, obj):
        pass

    @classmethod
    @abc.abstractmethod
    def validate_dependency_registration(cls, params, obj):
        pass

    @abc.abstractmethod
    def invocation_flow(self, sreq):
        pass

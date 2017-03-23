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

import mock
import unittest

from storlets.gateway.gateways.stub import StorletGatewayStub
from storlets.swift_middleware import storlet_handler

from tests.unit import FakeLogger
from tests.unit.swift_middleware import FakeApp


def create_handler_config(exec_server):
    return {'execution_server': exec_server,
            'gateway_module': StorletGatewayStub}


class BaseTestStorletMiddleware(unittest.TestCase):
    def setUp(self, exec_server='proxy'):
        self.exec_server = exec_server
        self.conf = create_handler_config(exec_server)
        self.logger = FakeLogger()
        self.base_app = FakeApp()

    def tearDown(self):
        pass

    def get_app(self, app, global_conf, **local_conf):
        with mock.patch('storlets.swift_middleware.storlet_handler.'
                        'get_logger') as get_fake_logger:
            get_fake_logger.return_value = self.logger
            factory = storlet_handler.filter_factory(global_conf, **local_conf)
            return factory(app)

    def get_response(self, req):
        app = self.get_app(self.base_app, self.conf)
        return req.get_response(app)

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

import copy
import mock
import unittest

from storlet_middleware import storlet_handler

from tests.unit.swift import FakeLogger
from tests.unit.swift.storlet_middleware import FakeApp


# TODO(takashi): take these values from config file
DEFAULT_CONFIG = {
    'storlet_container': 'storlet',
    'storlet_dependency': 'dependency',
    'storlet_timeout': '40',
    'storlet_gateway_module':
        'storlet_gateway.gateways.stub:StorletGatewayStub',
    'storlet_gateway_conf': '/etc/swift/storlet_stub_gateway.conf',
    'execution_server': 'proxy'}


class BaseTestStorletMiddleware(unittest.TestCase):
    def setUp(self):
        self.conf = copy.copy(DEFAULT_CONFIG)
        self.base_app = FakeApp()

    def tearDown(self):
        pass

    def get_app(self, app, global_conf, **local_conf):
        with mock.patch('storlet_middleware.storlet_handler.get_logger') as \
            get_fake_logger:
            get_fake_logger.return_value = FakeLogger()
            factory = storlet_handler.filter_factory(global_conf, **local_conf)
            return factory(app)

    def test_load_app(self):
        try:
            self.get_app(self.base_app, self.conf)
        except Exception:
            self.fail('Application loading got an error')

    def get_response(self, req):
        app = self.get_app(self.base_app, self.conf)
        return req.get_response(app)

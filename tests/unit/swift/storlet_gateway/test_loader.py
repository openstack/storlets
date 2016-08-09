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
import unittest
from storlet_gateway.common.exceptions import StorletGatewayLoadError
from storlet_gateway.loader import load_gateway
from storlet_gateway.gateways.stub import StorletGatewayStub


class TestLoader(unittest.TestCase):
    def setUp(self):
        pass

    def test_load_gateway(self):
        self.assertEqual(
            StorletGatewayStub,
            load_gateway('storlet_gateway.gateways.stub:StorletGatewayStub'))

        with self.assertRaises(StorletGatewayLoadError):
            load_gateway('storlet_gateway.gateways.foo:StorletGatewayFoo')

        with self.assertRaises(StorletGatewayLoadError):
            load_gateway('storlet_gateway.gateways.stub:StorletGatewayFoo')

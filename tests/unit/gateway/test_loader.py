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
from storlets.gateway.common.exceptions import StorletGatewayLoadError
from storlets.gateway.loader import load_gateway
from storlets.gateway.gateways.stub import StorletGatewayStub
from storlets.gateway.gateways.docker import StorletGatewayDocker


class TestLoader(unittest.TestCase):
    def setUp(self):
        pass

    def test_load_gateway_entry_point(self):
        # existing entry point
        self.assertEqual(
            StorletGatewayStub,
            load_gateway('stub'))

        self.assertEqual(
            StorletGatewayDocker,
            load_gateway('docker'))

        # If the given entry point does not exist
        with self.assertRaises(StorletGatewayLoadError):
            load_gateway('foo')

    def test_load_gateway_full_class_path(self):
        # If the given class path exists
        self.assertEqual(
            StorletGatewayStub,
            load_gateway('storlets.gateway.gateways.stub.StorletGatewayStub'))

        self.assertEqual(
            StorletGatewayDocker,
            load_gateway('storlets.gateway.gateways.docker.'
                         'StorletGatewayDocker'))

        # If module does not exist
        with self.assertRaises(StorletGatewayLoadError):
            load_gateway('storlets.gateway.gateways.another_stub.'
                         'StorletGatewayStub')

        # If class does not exist
        with self.assertRaises(StorletGatewayLoadError):
            load_gateway('storlets.gateway.gateways.stub.'
                         'StorletGatewayAnotherStub')


if __name__ == '__main__':
    unittest.main()

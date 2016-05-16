'''----------------------------------------------------------------
Copyright (c) 2010-2016 OpenStack Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
----------------------------------------------------------------'''

from swiftclient import client as swift_client
from __init__ import StorletBaseFunctionalTest


class TestCapabilities(StorletBaseFunctionalTest):
    def setUp(self):
        super(TestCapabilities, self).setUp()

    def test_get_capabilities(self):
        conn = swift_client.Connection(self.conf.auth_uri,
                                       self.conf.user,
                                       self.conf.password,
                                       insecure=True,
                                       tenant_name=self.conf.tenant_name,
                                       auth_version=self.conf.auth_version)
        info = conn.get_capabilities()
        self.assertTrue('storlet_handler' in info)
        options = info['storlet_handler']
        # TODO(eranr): take values from conf
        self.assertEqual(options['storlet_dependency'], 'dependency')
        self.assertEqual(options['storlet_container'], 'storlet')
        self.assertEqual(options['storlet_gateway_class'],
                         'StorletGatewayDocker')

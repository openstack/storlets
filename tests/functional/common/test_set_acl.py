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

import uuid
from swiftclient import client as swift_client
from tests.functional import StorletBaseFunctionalTest
import unittest


class TestSetACL(StorletBaseFunctionalTest):
    def setUp(self):
        super(TestSetACL, self).setUp()
        self.container = str(uuid.uuid4())
        swift_client.put_container(self.url,
                                   self.token,
                                   self.container)

    def tearDown(self):
        swift_client.delete_container(self.url,
                                      self.token,
                                      self.container)

    def test_set_acl(self):
        headers = {'X-Container-Read': 'adam'}
        swift_client.post_container(self.url,
                                    self.token,
                                    self.container,
                                    headers)

        headers = {'X-Storlet-Container-Read': 'john',
                   'X-Storlet-Name': 'mystorlet-1.0.jar'}
        swift_client.post_container(self.url,
                                    self.token,
                                    self.container,
                                    headers)

        headers = swift_client.head_container(self.url,
                                              self.token,
                                              self.container)
        read_acl = headers['x-container-read']
        expected_acl = ('adam,.r:storlets'
                        '.john_mystorlet-1.0.jar')
        self.assertEqual(expected_acl, read_acl)


if __name__ == '__main__':
    unittest.main()

# Copyright (c) 2010-2017 OpenStack Foundation
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

from swiftclient import client
from tests.functional.python import StorletPythonFunctionalTest
import unittest


class TestSymlink(StorletPythonFunctionalTest):
    def setUp(self):
        self.storlet_log = 'simple-symlink.log'
        self.additional_headers = {}
        self.content = b'abcdefghijklmonp'
        super(TestSymlink, self).setUp(
            storlet_dir='simple',
            storlet_name='simple.py',
            storlet_main='simple.SimpleStorlet',
            storlet_file='source.txt',
            headers={})

        symlink_target = '/'.join([self.container, self.storlet_file])
        client.put_object(self.url, self.token, self.container, 'test_link',
                          '', headers={'X-Symlink-Target': symlink_target})

    def test_get(self):
        req_headers = {'X-Run-Storlet': self.storlet_name}
        headers, content = client.get_object(
            self.url, self.token, self.container, self.storlet_file,
            headers=req_headers)
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content, content)

        req_headers = {'X-Run-Storlet': self.storlet_name}
        headers, content = client.get_object(
            self.url, self.token, self.container, 'test_link',
            headers=req_headers)
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content, content)


class TestSymlinkOnProxy(TestSymlink):
    def setUp(self):
        super(TestSymlinkOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

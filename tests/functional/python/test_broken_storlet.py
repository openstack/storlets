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

from swiftclient import client
from swiftclient.exceptions import ClientException
from tests.functional.python import StorletPythonFunctionalTest
import unittest
from storlets.agent.common.utils import DEFAULT_PY3


class TestBrokenStorlet(StorletPythonFunctionalTest):
    def setUp(self, version=None):
        self.storlet_log = 'broken.log'
        self.content = 'abcdefghijklmonp'
        self.additional_headers = {}
        super(TestBrokenStorlet, self).setUp(
            storlet_dir='broken',
            storlet_name='broken.py',
            storlet_main='broken.BrokenStorlet',
            storlet_file='source.txt',
            version=version)

    def test_get(self):
        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name}
        with self.assertRaises(ClientException) as cm:
            client.get_object(
                self.url, self.token, self.container, self.storlet_file,
                response_dict=resp, headers=req_headers)
        e = cm.exception
        self.assertEqual(e.http_status, 503)


class TestBrokenStorletRunPy3(TestBrokenStorlet):
    def setUp(self):
        super(TestBrokenStorletRunPy3, self).setUp(version=DEFAULT_PY3)


if __name__ == '__main__':
    unittest.main()

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
from tests.functional.python import StorletPythonFunctionalTest


class TestSimpleStorlet(StorletPythonFunctionalTest):
    def setUp(self):
        self.storlet_log = 'simple.log'
        self.content = 'abcdefghijklmonp'
        self.additional_headers = {}
        super(TestSimpleStorlet, self).setUp('simple', 'simple.py',
                                             'simple.SimpleStorlet',
                                             'myobjects', 'source.txt')

    def test_get(self):
        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name}
        headers, content = client.get_object(
            self.url, self.token, self.container, self.storlet_file,
            response_dict=resp, headers=req_headers)
        self.assertEqual(200, resp['status'])
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content, content)

    def test_range_get(self):
        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name,
                       'X-Storlet-Range': 'bytes=1-4'}
        headers, content = client.get_object(
            self.url, self.token, self.container, self.storlet_file,
            response_dict=resp, headers=req_headers)
        self.assertEqual(200, resp['status'])
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content[1:5], content)

    def test_put(self):
        objname = self.storlet_file + '-put'

        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name}
        client.put_object(
            self.url, self.token, self.container, objname,
            self.content, response_dict=resp, headers=req_headers)
        self.assertEqual(201, resp['status'])

        resp = dict()
        headers, content = client.get_object(
            self.url, self.token, self.container, objname,
            response_dict=resp)
        self.assertEqual(200, resp['status'])
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content, content)

        resp = dict()
        client.delete_object(
            self.url, self.token, self.container, objname,
            response_dict=resp)
        self.assertEqual(204, resp['status'])


class TestSimpleStorletOnProxy(TestSimpleStorlet):
    def setUp(self):
        super(TestSimpleStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}

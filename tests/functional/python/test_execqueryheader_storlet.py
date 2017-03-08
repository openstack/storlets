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

import random
import string
from swiftclient import client
from tests.functional.python import StorletPythonFunctionalTest
import unittest


class TestExecQueryHeaderStorlet(StorletPythonFunctionalTest):
    def setUp(self):
        self.additional_headers = {}
        super(TestExecQueryHeaderStorlet, self).setUp(
            storlet_dir='exec_query_header',
            storlet_name='exec_query_header.py',
            storlet_main='exec_query_header.ExecQueryHeaderStorlet',
            storlet_file='source.txt',
            headers={})

    def invoke_storlet(self, op, params=None, header_parameters=False):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        if params is not None:
            if header_parameters:
                querystring = None
                count = 1
                for key in params:
                    headers['X-Storlet-Parameter-' + str(count)] = \
                        key + ':' + params[key]
                    count = count + 1
            else:
                querystring = '&'.join(['%s=%s' % (k, v)
                                       for k, v in params.items()])
        else:
            querystring = None

        if op == 'GET':
            # Get original object
            original_h, original_c = client.get_object(self.url, self.token,
                                                       self.container,
                                                       self.storlet_file,
                                                       response_dict=dict())
            file_length = int(original_h['content-length'])
            processed_h, returned_c = client.get_object(
                self.url, self.token,
                self.container, self.storlet_file,
                query_string=querystring, response_dict=dict(),
                headers=headers, resp_chunk_size=file_length)
            processed_c = ''
            for chunk in returned_c:
                if chunk:
                    processed_c += chunk

            for param_key, param_value in params.items():
                mdv = processed_h['X-Object-Meta-%s'.lower() % param_key]
                self.assertEqual(mdv, param_value)

        if op == 'PUT':
            # PUT a random file
            response = dict()
            uploaded_c = ''.join(random.choice(string.ascii_uppercase +
                                 string.digits) for _ in range(1024))
            content_length = None
            client.put_object(self.url, self.token, self.container,
                              'random_source',
                              uploaded_c, content_length, None, None,
                              "application/octet-stream", headers, None, None,
                              querystring, response)
            resp_headers, saved_c = client.get_object(self.url, self.token,
                                                      self.container,
                                                      'random_source',
                                                      response_dict=dict())

            for param_key, param_value in params.items():
                mdv = resp_headers['X-Object-Meta-%s'.lower() % param_key]
                self.assertEqual(mdv, param_value)

    def test_put_execute_with_header(self):
        self.invoke_storlet('PUT', {'key1': 'value1'},
                            header_parameters=True)
        self.invoke_storlet('PUT', {'key1': 'value1', 'key2': 'value2'},
                            header_parameters=True)

    def test_put_execute_with_query(self):
        self.invoke_storlet('PUT', {'key1': 'value1'})
        self.invoke_storlet('PUT', {'key1': 'value1', 'key2': 'value2'})

    def test_get_execute_with_header(self):
        self.invoke_storlet('GET', {'key1': 'value1'},
                            header_parameters=True)
        self.invoke_storlet('GET', {'key1': 'value1', 'key2': 'value2'},
                            header_parameters=True)

    def test_get_execute_with_query(self):
        self.invoke_storlet('GET', {'key1': 'value1'})
        self.invoke_storlet('GET', {'key1': 'value1', 'key2': 'value2'})


class TestExecQueryHeaderStorletOnProxy(TestExecQueryHeaderStorlet):
    def setUp(self):
        super(TestExecQueryHeaderStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

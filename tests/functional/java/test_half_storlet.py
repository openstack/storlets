# Copyright IBM Corp. 2015, 2015 All Rights Reserved
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
from swiftclient import client as c
from tests.functional.java import StorletJavaFunctionalTest
import unittest


class TestHalfIdentityStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = ''
        self.additional_headers = {}
        headers = {'X-Object-Meta-Testkey': 'tester'}
        main_class = 'org.openstack.storlet.half.HalfStorlet'
        super(TestHalfIdentityStorlet, self).setUp('HalfStorlet',
                                                   'halfstorlet-1.0.jar',
                                                   main_class,
                                                   'source.txt',
                                                   headers=headers)

    def invoke_storlet(self, op, params=None, global_params=None,
                       headers=None):
        if params is not None:
            querystring = ''
            for key in params:
                querystring += '%s=%s,' % (key, params[key])
            querystring = querystring[:-1]
        else:
            querystring = None

        req_headers = {'X-Run-Storlet': self.storlet_name}
        req_headers.update(self.additional_headers)
        if headers:
            req_headers.update(headers)

        if op == 'GET':
            # Get original object
            original_h, original_c = \
                c.get_object(self.url, self.token, self.container,
                             self.storlet_file,
                             response_dict=dict())
            # print original_headers
            file_length = int(original_h['content-length'])
            processed_h, returned_c = \
                c.get_object(self.url, self.token, self.container,
                             self.storlet_file,
                             query_string=querystring, response_dict=dict(),
                             headers=req_headers, resp_chunk_size=file_length)
            processed_c = ''
            for chunk in returned_c:
                if chunk:
                    processed_c += chunk

            self.assertEqual(original_h['X-Object-Meta-Testkey'.lower()],
                             processed_h['X-Object-Meta-Testkey'.lower()])
            return processed_c

        if op == 'PUT':
            # PUT a random file
            response = dict()
            uploaded_content = ''.join(random.choice(string.ascii_uppercase +
                                       string.digits) for _ in range(1024))
            random_md = ''.join(random.choice(string.ascii_uppercase +
                                string.digits) for _ in range(32))
            # content_length = 1024
            content_length = None
            headers = {'X-Run-Storlet': self.storlet_name,
                       'X-Object-Meta-Testkey': random_md}
            headers.update(self.additional_headers)
            c.put_object(self.url, self.token, self.container,
                         'half_random_source',
                         uploaded_content, content_length, None, None,
                         "application/octet-stream", headers, None, None,
                         querystring, response)
            resp_headers, saved_content = c.get_object(self.url, self.token,
                                                       self.container,
                                                       'half_random_source',
                                                       response_dict=dict())

            if params is not None and params.get('double', None) == 'true':
                self.assertEqual(uploaded_content, saved_content[:1024])
                self.assertEqual(uploaded_content, saved_content[1024:])
            else:
                self.assertEqual(uploaded_content, saved_content)

            if params is not None and params.get('execute', None) is not None:
                self.assertEqual(
                    '42',
                    resp_headers['X-Object-Meta-Execution result'.lower()])

            self.assertEqual(random_md,
                             resp_headers['X-Object-Meta-Testkey'.lower()])

    def test_get(self):
        res = self.invoke_storlet('GET')
        self.assertEqual('acegikmn', res)

    def test_get_range(self):
        res = self.invoke_storlet(
            'GET',
            headers={'X-Storlet-Range': 'bytes=5-10'})
        self.assertEqual('fhj', res)


class TestHalfIdentityStorletOnProxy(TestHalfIdentityStorlet):
    def setUp(self):
        super(TestHalfIdentityStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

import os
import random
import string
from swiftclient import client as c
from nose.plugins.attrib import attr
from __init__ import StorletFunctionalTest


class TestIdentityStorlet(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'IdentityStorlet'
        self.storlet_name = 'identitystorlet-1.0.jar'
        self.storlet_main = 'com.ibm.storlet.identity.IdentityStorlet'
        self.storlet_log = 'identitystorlet-1.0.log'
        self.headers = {'X-Object-Meta-Testkey': 'tester'}
        self.storlet_file = 'source.txt'
        self.container = 'myobjects'
        self.dep_names = ['get42']
        self.additional_headers = {}
        super(TestIdentityStorlet, self).setUp()

    def invoke_storlet(self, op, params=None, global_params=None,
                       header_parameters=False):
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
                querystring = ''
                for key in params:
                    querystring += '%s=%s,' % (key, params[key])
                querystring = querystring[:-1]
        else:
            querystring = None

        if op == 'GET':
            # Get original object
            original_h, original_c = c.get_object(self.url, self.token,
                                                  'myobjects',
                                                  self.storlet_file,
                                                  response_dict=dict())
            # print original_headers
            file_length = int(original_h['content-length'])
            processed_h, returned_c = c.get_object(
                self.url, self.token,
                self.container, self.storlet_file,
                query_string=querystring, response_dict=dict(),
                headers=headers, resp_chunk_size=file_length)
            processed_c = ''
            for chunk in returned_c:
                if chunk:
                    processed_c += chunk

            if params is not None and params.get('execute', None) is not None:
                mdv = processed_h['X-Object-Meta-Execution result'.lower()]
                self.assertEqual(mdv, '42')
            if params is not None and params.get('double', None) == 'true':
                self.assertEqual(original_c, processed_c[:file_length])
                self.assertEqual(original_c, processed_c[file_length:])
            else:
                self.assertEqual(original_c, processed_c)
            self.assertEqual(original_h['X-Object-Meta-Testkey'.lower()],
                             processed_h['X-Object-Meta-Testkey'.lower()])

        if op == 'PUT':
            # PUT a random file
            response = dict()
            uploaded_c = ''.join(random.choice(string.ascii_uppercase +
                                 string.digits) for _ in range(1024))
            random_md = ''.join(random.choice(string.ascii_uppercase +
                                string.digits) for _ in range(32))
            content_length = None
            headers['X-Object-Meta-Testkey'] = random_md
            c.put_object(self.url, self.token, self.container,
                         'identity_random_source',
                         uploaded_c, content_length, None, None,
                         "application/octet-stream", headers, None, None,
                         querystring, response)
            resp_headers, saved_c = c.get_object(self.url, self.token,
                                                 'myobjects',
                                                 'identity_random_source',
                                                 response_dict=dict())

            if params is not None and params.get('double', None) == 'true':
                assert(uploaded_c == saved_c[:1024])
                assert(uploaded_c == saved_c[1024:])
            else:
                assert(uploaded_c == saved_c)

            if params is not None and params.get('execute', None) is not None:
                mdv = resp_headers['X-Object-Meta-Execution result'.lower()]
                self.assertEqual(mdv, '42')

            self.assertEqual(resp_headers['X-Object-Meta-Testkey'.lower()],
                             random_md)

    @attr('slow')
    def test_put_1GB_file(self):
        GBFile = open('/tmp/1GB_file', 'w')
        for _ in range(128):
            uploaded_content = ''.join('1' for _ in range(8 * 1024 * 1024))
            GBFile.write(uploaded_content)
        GBFile.close()

        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        GBFile = open('/tmp/1GB_file', 'r')
        response = dict()
        c.put_object(self.url, self.token,
                     self.container, '1GBFile', GBFile,
                     1024 * 1024 * 1024, None, None,
                     "application/octet-stream",
                     headers, None, None, None, response)
        status = response.get('status')
        self.assertTrue(status in [200, 201])
        os.remove('/tmp/1GB_file')

    def test_put(self):
        self.invoke_storlet('PUT')

    def test_put_execute(self):
        self.invoke_storlet('PUT', {'execute': 'true'})
        self.invoke_storlet('PUT', {'execute': 'true'},
                            header_parameters=True)

    def test_put_double(self):
        self.invoke_storlet('PUT', {'double': 'true'})
        self.invoke_storlet('PUT', {'double': 'true'},
                            header_parameters=True)

    def test_get(self):
        self.invoke_storlet('GET')

    def test_get_double(self):
        self.invoke_storlet('GET', {'double': 'true'})
        self.invoke_storlet('GET', {'double': 'true'},
                            header_parameters=True)

    def test_get_execute(self):
        self.invoke_storlet('GET', {'execute': 'true'})
        self.invoke_storlet('GET', {'execute': 'true'},
                            header_parameters=True)


class TestIdentityStorletOnProxy(TestIdentityStorlet):
    def setUp(self):
        super(TestIdentityStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}

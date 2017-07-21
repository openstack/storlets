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

import os
import random
import string
from swiftclient import client as c
from nose.plugins.attrib import attr
from contextlib import contextmanager
from tests.functional.java import StorletJavaFunctionalTest
import unittest


class TestIdentityStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = 'identitystorlet-1.0.log'
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.identity.IdentityStorlet'
        headers = {'X-Object-Meta-Testkey': 'tester'}
        super(TestIdentityStorlet, self).setUp('IdentityStorlet',
                                               'identitystorlet-1.0.jar',
                                               main_class,
                                               'source.txt',
                                               ['get42'],
                                               headers)

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
                querystring = '&'.join(['%s=%s' % (k, v)
                                       for k, v in params.items()])
        else:
            querystring = None

        if op == 'GET':
            # Get original object
            original_h, original_c = c.get_object(self.url, self.token,
                                                  self.container,
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
                self.assertEqual('42', mdv)
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
                                                 self.container,
                                                 'identity_random_source',
                                                 response_dict=dict())

            if params is not None and params.get('double', None) == 'true':
                assert(uploaded_c == saved_c[:1024])
                assert(uploaded_c == saved_c[1024:])
            else:
                assert(uploaded_c == saved_c)

            if params is not None and params.get('execute', None) is not None:
                mdv = resp_headers['X-Object-Meta-Execution result'.lower()]
                self.assertEqual('42', mdv)

            self.assertEqual(random_md,
                             resp_headers['X-Object-Meta-Testkey'.lower()])

    @contextmanager
    def _filecontext(self, path):
        yield
        try:
            os.remove(path)
        except Exception:
            pass

    @attr('slow')
    def test_put_1GB_file(self):
        gf_file_path = '/tmp/1GB_file'
        with self._filecontext(gf_file_path):
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
            self.assertIn(status, [200, 201])

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

    def _test_get_range(self, start, end, expected):
        srange = 'bytes=%d-%d' % (start, end)
        headers = {'X-Run-Storlet': self.storlet_name,
                   'X-Storlet-Range': srange}
        headers.update(self.additional_headers)
        junk, content = c.get_object(self.url, self.token,
                                     self.container,
                                     'small',
                                     headers=headers,
                                     response_dict=dict())
        self.assertEqual(expected, content)

    def test_get_ranges(self):
        response = dict()
        c.put_object(self.url, self.token,
                     self.container, 'small',
                     '0123456789abcd',
                     response_dict=response)

        self._test_get_range(0, 0, '0')
        self._test_get_range(0, 10, '0123456789a')
        self._test_get_range(2, 10, '23456789a')
        self._test_get_range(10, 13, 'abcd')
        self._test_get_range(10, 14, 'abcd')
        self._test_get_range(10, 15, 'abcd')


class TestIdentityStorletOnProxy(TestIdentityStorlet):
    def setUp(self):
        super(TestIdentityStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

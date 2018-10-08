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

import json
import random
import string
from swiftclient import client
from nose.plugins.attrib import attr
from tests.functional.python import StorletPythonFunctionalTest
import unittest


class TestSLO(StorletPythonFunctionalTest):
    def setUp(self):
        self.storlet_log = 'simple.log'
        self.additional_headers = {}
        self.chunks = []
        super(TestSLO, self).setUp(
            storlet_dir='simple',
            storlet_name='simple.py',
            storlet_main='simple.SimpleStorlet',
            storlet_file=None,
            headers={})

        for cont in ('container1', 'container2', 'container3'):
            self.create_container(cont)
        self.create_local_chunks()
        self.put_SLO()
        self.get_SLO()

    def create_local_chunks(self):
        for i in range(9):
            self.chunks.append(
                ''.join([random.choice(string.ascii_uppercase + string.digits)
                         for _ in range(1024 * 1024)]))

    def get_SLO(self):
        response = dict()
        headers, body = client.get_object(self.url, self.token, self.container,
                                          'assembly', http_conn=None,
                                          resp_chunk_size=1024 * 1024,
                                          query_string=None,
                                          response_dict=response,
                                          headers=None)

        for (i, chunk) in enumerate(body):
            self.assertEqual(chunk, self.chunks[i])

    def put_SLO(self):
        assembly = []
        for i in range(9):
            oname = 'slo_chunk_%d' % i
            content_length = None
            response = dict()
            client.put_object(self.url, self.token,
                              self.container, oname, self.chunks[i],
                              content_length, None, None,
                              "application/octet-stream",
                              None, None, None, None, response)
            status = response.get('status')
            self.assertEqual(2, status // 100)

            headers = response.get('headers')
            segment = dict()
            segment['path'] = '%s/%s' % (self.container, oname)
            segment['size_bytes'] = 1024 * 1024
            segment['etag'] = headers['etag']
            assembly.append(segment)

        content_length = None
        response = dict()
        headers = {'x-object-meta-prop1': 'val1'}
        client.put_object(self.url, self.token, self.container,
                          'assembly', json.dumps(assembly),
                          content_length=None, etag=None, chunk_size=None,
                          headers=headers,
                          query_string='multipart-manifest=put',
                          response_dict=response)
        status = response.get('status')
        self.assertEqual(2, status // 100)

    def compare_slo_to_chunks(self, body):
        for (i, chunk) in enumerate(body):
            if chunk:
                if i in range(9):
                    self.assertEqual(chunk, self.chunks[i])
                else:
                    aux_content = ''
                    for j in range(1, 4):
                        oname = 'aux_file%d' % j
                        with open(oname, 'r') as f:
                            aux_content += f.read()
                    self.asertEqual(chunk, aux_content)

    @attr('slow')
    def test_get_SLO(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        response = dict()
        headers, body = client.get_object(self.url, self.token,
                                          self.container, 'assembly',
                                          query_string=None,
                                          response_dict=response,
                                          resp_chunk_size=1024 * 1024,
                                          headers=headers)
        self.compare_slo_to_chunks(body)


class TestSLOOnProxy(TestSLO):
    def setUp(self):
        super(TestSLOOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

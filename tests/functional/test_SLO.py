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

import json
import os
import random
import string
from swiftclient import client as c
from __init__ import StorletFunctionalTest


def create_local_chunks():
    for i in range(1, 10):
        oname = '/tmp/slo_chunk_%d' % i
        f = open(oname, 'w')
        f.write(''.join(random.choice(string.ascii_uppercase + string.digits)
                for _ in range(1048576)))
        f.close()


def delete_local_chunks():
    for i in range(1, 10):
        oname = '/tmp/slo_chunk_%d' % i
        os.remove(oname)


def create_container(url, token, name):
    response = dict()
    c.put_container(url, token, name, headers=None, response_dict=response)
    status = response.get('status')
    assert (status >= 200 or status < 300)


class TestSLO(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'IdentityStorlet'
        self.storlet_name = 'identitystorlet-1.0.jar'
        self.storlet_main = 'com.ibm.storlet.identity.IdentityStorlet'
        self.storlet_log = 'identitystorlet-1.0.log'
        self.headers = None
        self.storlet_file = ''
        self.container = 'myobjects'
        self.dep_names = []
        super(TestSLO, self).setUp()

        create_container(self.url, self.token, 'myobjects')
        create_container(self.url, self.token, 'container1')
        create_container(self.url, self.token, 'container2')
        create_container(self.url, self.token, 'container3')
        create_local_chunks()
        self.put_SLO()
        self.get_SLO()

    def tearDown(self):
        delete_local_chunks()

    def get_SLO(self):
        response = dict()
        headers, body = c.get_object(self.url, self.token,
                                     self.container, 'assembly',
                                     http_conn=None, resp_chunk_size=1048576,
                                     query_string=None, response_dict=response,
                                     headers=None)

        i = 1
        for chunk in body:
            oname = '/tmp/slo_chunk_%d' % i
            f = open(oname, 'r')
            file_content = f.read()
            # print '%s    %s' % (chunk[:10], file_content[:10])
            # print '%d    %d' % (len(chunk), len(file_content))
            self.assertEqual(chunk, file_content)
            f.close()
            i = i + 1

    def put_SLO(self):
        # Create temp files
        assembly = []
        for i in range(1, 10):
            oname = '/tmp/slo_chunk_%d' % i
            f = open(oname, 'r')
            content_length = None
            response = dict()
            c.put_object(self.url, self.token,
                         self.container, oname, f,
                         content_length, None, None,
                         "application/octet-stream",
                         None, None, None, None, response)
            f.close()
            status = response.get('status')
            self.assertTrue(status >= 200 and status < 300)

            headers = response.get('headers')
            segment = dict()
            segment['path'] = 'myobjects/%s' % oname
            segment['size_bytes'] = 1048576
            segment['etag'] = headers['etag']
            assembly.append(segment)

        content_length = None
        response = dict()
        headers = {'x-object-meta-prop1': 'val1'}
        c.put_object(self.url, self.token, self.container,
                     'assembly', json.dumps(assembly),
                     content_length=None, etag=None, chunk_size=None,
                     headers=headers, query_string='multipart-manifest=put',
                     response_dict=response)
        status = response.get('status')
        self.assertTrue(status >= 200 and status < 300)

    def compare_slo_to_chunks(self, body):
        i = 1
        for chunk in body:
            if chunk:
                if i < 10:
                    oname = '/tmp/slo_chunk_%d' % i
                    f = open(oname, 'r')
                    file_content = f.read()
                    # print '%s    %s' % (chunk[:10], file_content[:10])
                    # print '%d    %d' % (len(chunk), len(file_content))
                    self.assertEqual(chunk, file_content)
                    f.close()
                    i = i + 1
                else:
                    aux_content = ''
                    for j in range(1, 4):
                        oname = '/tmp/aux_file%d' % j
                        f = open(oname, 'r')
                        aux_content += f.read()
                        f.close()
                    self.ssertEqual(chunk, aux_content)

    def test_get_SLO(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        response = dict()
        headers, body = c.get_object(self.url, self.token,
                                     'myobjects', 'assembly',
                                     query_string=None,
                                     response_dict=response,
                                     resp_chunk_size=1048576,
                                     headers=headers)
        self.compare_slo_to_chunks(body)

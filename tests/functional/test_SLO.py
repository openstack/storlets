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

from __init__ import ACCOUNT
from __init__ import AUTH_IP
from __init__ import AUTH_PORT
from __init__ import PASSWORD
from __init__ import put_storlet_object
from __init__ import USER_NAME
import json
import os
import random
import string
from swiftclient import client as c
from test_identity_storlet import deploy_identity_storlet
from test_identity_storlet import IDENTITY_STORLET_NAME
import unittest


SLOIDENTITY_PATH_TO_BUNDLE = '../../StorletSamples/SLOIdentityStorlet/bin'
SLOIDENTITY_STORLET_NAME = 'sloidentitystorlet-1.0.jar'


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


def put_SLO(url, token):
    # Create temp files
    assembly = []
    for i in range(1, 10):
        oname = '/tmp/slo_chunk_%d' % i
        f = open(oname, 'r')
        content_length = None
        response = dict()
        c.put_object(url, token, 'myobjects', oname, f,
                     content_length, None, None, "application/octet-stream",
                     None, None, None, None, response)
        f.close()
        status = response.get('status')
        assert (status >= 200 and status < 300)

        headers = response.get('headers')
        segment = dict()
        segment['path'] = 'myobjects/%s' % oname
        segment['size_bytes'] = 1048576
        segment['etag'] = headers['etag']
        assembly.append(segment)

    content_length = None
    response = dict()
    headers = {'x-object-meta-prop1': 'val1'}
    c.put_object(url, token, 'myobjects', 'assembly', json.dumps(assembly),
                 content_length=None, etag=None, chunk_size=None,
                 headers=headers, query_string='multipart-manifest=put',
                 response_dict=response)
    status = response.get('status')
    assert (status >= 200 and status < 300)


def get_SLO(url, token):
    response = dict()
    headers, body = c.get_object(url, token, 'myobjects', 'assembly',
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
        assert(chunk == file_content)
        f.close()
        i = i + 1


def compare_slo_to_chunks(body):
    i = 1
    for chunk in body:
        if chunk:
            if i < 10:
                oname = '/tmp/slo_chunk_%d' % i
                f = open(oname, 'r')
                file_content = f.read()
                # print '%s    %s' % (chunk[:10], file_content[:10])
                # print '%d    %d' % (len(chunk), len(file_content))
                assert(chunk == file_content)
                f.close()
                i = i + 1
            else:
                aux_content = ''
                for j in range(1, 4):
                    oname = '/tmp/aux_file%d' % j
                    f = open(oname, 'r')
                    aux_content += f.read()
                    f.close()
                assert(chunk == aux_content)


def invoke_identity_on_get_SLO(url, token):
    metadata = {'X-Run-Storlet': IDENTITY_STORLET_NAME}
    response = dict()
    headers, body = c.get_object(url, token,
                                 'myobjects', 'assembly',
                                 query_string=None,
                                 response_dict=response,
                                 resp_chunk_size=1048576,
                                 headers=metadata)
    compare_slo_to_chunks(body)


def invoke_identity_on_get_SLO_double(url, token):
    metadata = {'X-Run-Storlet': IDENTITY_STORLET_NAME}
    response = dict()
    headers, body = c.get_object(url, token,
                                 'myobjects',
                                 'assembly',
                                 query_string='double=true',
                                 response_dict=response,
                                 resp_chunk_size=2048,
                                 headers=metadata)

    i = 1
    oname = '/tmp/slo_chunk_%d' % i
    f = open(oname, 'r')
    file_content = f.read()

    j = 0  # Count chunks in file 1...1024
    for chunk in body:
        file_fragment = file_content[j * 1024:(j + 1) * 1024]
        chunk_framgment_low = chunk[0:1024]
        chunk_framgment_high = chunk[1024:2048]
        assert(chunk_framgment_low == file_fragment)
        assert(chunk_framgment_high == file_fragment)
        j = j + 1
        if j == 1024:
            i = i + 1
            if i == 10:
                break
            f.close()
            oname = '/tmp/slo_chunk_%d' % i
            f = open(oname, 'r')
            file_content = f.read()
            j = 0
    assert i == 10


def invoke_identity_on_partial_get_SLO(url, token):
    metadata = {'X-Run-Storlet': IDENTITY_STORLET_NAME}
    for i in range(5):
        response = dict()
        headers, body = c.get_object(url, token,
                                     'myobjects',
                                     'assembly',
                                     query_string=None,
                                     response_dict=response,
                                     resp_chunk_size=1048576,
                                     headers=metadata)

        j = 1
        for chunk in body:
            j = j + 1
            if j == 5:
                break

# def delete_files():
#     for i in range(1,4):
#         fname = '/tmp/aux_file%d' % i
#         os.remove(fname)


def create_container(url, token, name):
    response = dict()
    c.put_container(url, token, name, headers=None, response_dict=response)
    status = response.get('status')
    assert (status >= 200 or status < 300)


def deploy_sloidentity_storlet(url, token):
    response = dict()
    c.put_container(url, token, 'mysloobject', None, None, response)
    status = response.get('status')
    assert (status >= 200 or status < 300)

    put_storlet_object(url, token,
                       SLOIDENTITY_STORLET_NAME,
                       SLOIDENTITY_PATH_TO_BUNDLE,
                       '',
                       'com.ibm.storlet.sloidentity.SLOIdentityStorlet')


class TestSLO(unittest.TestCase):
    def setUp(self):
        os_options = {'tenant_name': ACCOUNT}
        self.url, self.token = c.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT
                                          + "/v2.0", ACCOUNT + ":" + USER_NAME,
                                          PASSWORD, os_options=os_options,
                                          auth_version="2.0")
        create_container(self.url, self.token, 'myobjects')
        create_container(self.url, self.token, 'container1')
        create_container(self.url, self.token, 'container2')
        create_container(self.url, self.token, 'container3')
        create_local_chunks()
        put_SLO(self.url, self.token)
        get_SLO(self.url, self.token)
        deploy_identity_storlet(self.url, self.token)

    def tearDown(self):
        delete_local_chunks()

    def test_get_SLO(self):
        invoke_identity_on_get_SLO(self.url, self.token)

    # YM comment out 2 lines - temporary only!
        # progress_msg("Invoking storlet on SLO in GET with double")
    # invoke_identity_on_get_SLO_double(url, token)

    # progress_msg("Invoking storlet on SLO in partial GET")
    # invoke_identity_on_partial_get_SLO(url, token)

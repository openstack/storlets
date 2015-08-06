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

import random
import string
from swiftclient import client as c
from sys_test_params import ACCOUNT
from sys_test_params import AUTH_IP
from sys_test_params import AUTH_PORT
from sys_test_params import PASSWORD
from sys_test_params import USER_NAME

from storlets_test_utils import put_storlet_object

'''------------------------------------------------------------------------'''
# Test Constants
HALF_PATH_TO_BUNDLE = '../StorletSamples/HalfStorlet/bin/'
HALF_STORLET_NAME = 'halfstorlet-1.0.jar'
HALF_SOURCE_FILE = 'source.txt'

'''------------------------------------------------------------------------'''


def put_storlet_input_object(url, token):
    resp = dict()
    metadata = {'X-Object-Meta-Testkey': 'tester'}
    f = open('%s/%s' % (HALF_PATH_TO_BUNDLE, HALF_SOURCE_FILE), 'r')
    c.put_object(url, token, 'myobjects', HALF_SOURCE_FILE, f,
                 content_type="application/octet-stream",
                 headers=metadata,
                 response_dict=resp)
    f.close()
    status = resp.get('status')
    assert (status == 200 or status == 201)

'''------------------------------------------------------------------------'''


def deploy_storlet(url, token):
    # No need to create containers every time
    # put_storlet_containers(url, token)
    put_storlet_object(url, token,
                       HALF_STORLET_NAME,
                       HALF_PATH_TO_BUNDLE,
                       '',
                       'com.ibm.storlet.half.HalfStorlet')
    put_storlet_input_object(url, token)

'''------------------------------------------------------------------------'''


def invoke_storlet(url, token, op, params=None, global_params=None,
                   headers=None):
    if params is not None:
        querystring = ''
        for key in params:
            querystring += '%s=%s,' % (key, params[key])
        querystring = querystring[:-1]
    else:
        querystring = None

    metadata = {'X-Run-Storlet': HALF_STORLET_NAME}
    if headers:
        metadata.update(headers)

    if op == 'GET':
        # Get original object
        original_headers, original_content = \
            c.get_object(url, token, 'myobjects', HALF_SOURCE_FILE,
                         response_dict=dict())
        # print original_headers
        file_length = int(original_headers['content-length'])
        processed_headers, returned_content = \
            c.get_object(url, token, 'myobjects', HALF_SOURCE_FILE,
                         query_string=querystring, response_dict=dict(),
                         headers=metadata, resp_chunk_size=file_length)
        processed_content = ''
        for chunk in returned_content:
            if chunk:
                processed_content += chunk

        assert(original_headers['X-Object-Meta-Testkey'.lower()] ==
               processed_headers['X-Object-Meta-Testkey'.lower()])
        return processed_content

    if op == 'PUT':
        # PUT a random file
        response = dict()
        uploaded_content = ''.join(random.choice(string.ascii_uppercase +
                                   string.digits) for _ in range(1024))
        random_md = ''.join(random.choice(string.ascii_uppercase +
                            string.digits) for _ in range(32))
        # content_length = 1024
        content_length = None
        headers = {'X-Run-Storlet': HALF_STORLET_NAME,
                   'X-Object-Meta-Testkey': random_md}
        c.put_object(url, token, 'myobjects', 'half_random_source',
                     uploaded_content, content_length, None, None,
                     "application/octet-stream", headers, None, None,
                     querystring, response)
        resp_headers, saved_content = c.get_object(url, token, 'myobjects',
                                                   'half_random_source',
                                                   response_dict=dict())

        if params is not None and params.get('double', None) == 'true':
            assert(uploaded_content == saved_content[:1024])
            assert(uploaded_content == saved_content[1024:])
        else:
            assert(uploaded_content == saved_content)

        if params is not None and params.get('execute', None) is not None:
            assert(resp_headers['X-Object-Meta-Execution result'.lower()] ==
                   '42')

        assert(resp_headers['X-Object-Meta-Testkey'.lower()] == random_md)

'''------------------------------------------------------------------------'''


def main():
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth('http://' + AUTH_IP + ":"
                            + AUTH_PORT + '/v2.0',
                            ACCOUNT + ':' + USER_NAME,
                            PASSWORD,
                            os_options=os_options,
                            auth_version='2.0')

    print('Deploying Half storlet and dependencies')

    deploy_storlet(url, token)

    print("Invoking Half storlet on GET")
    assert (invoke_storlet(url, token, 'GET') == 'acegikmn')
    print("Invoking Half storlet on GET with byte ranges")
    assert (invoke_storlet(url, token, 'GET',
            headers={'range': 'bytes=5-10'}) == 'fhj')

'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main()

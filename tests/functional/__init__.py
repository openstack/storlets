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

'''
@author: gilv / cdoron / evgenyl
'''

from swiftclient import client as c

PROXY_PROTOCOL = 'HTTP'
AUTH_PROTOCOL = 'HTTP'
DEV_AUTH_IP = '127.0.0.1'
AUTH_IP = DEV_AUTH_IP
PROXY_PORT = '80'
AUTH_PORT = '5000'

ACCOUNT = 'service'
USER_NAME = 'swift'
PASSWORD = 'passw0rd'


def put_storlet_object(url, token, storlet_name, storlet_path,
                       dependency, main_class):
    metadata = {'X-Object-Meta-Storlet-Language': 'Java',
                'X-Object-Meta-Storlet-Interface-Version': '1.0',
                'X-Object-Meta-Storlet-Dependency': dependency,
                'X-Object-Meta-Storlet-Object-Metadata': 'no',
                'X-Object-Meta-Storlet-Main': main_class}
    f = open('%s/%s' % (storlet_path, storlet_name), 'r')
    content_length = None
    response = dict()
    c.put_object(url, token, 'storlet', storlet_name, f,
                 content_length, None, None,
                 "application/octet-stream", metadata,
                 None, None, None, response)
    f.close()
    status = response.get('status')
    assert (status == 200 or status == 201)


def put_file_as_storlet_input_object(url, token, local_path, local_file):
    resp = dict()
    f = open('%s/%s' % (local_path, local_file), 'r')
    c.put_object(url, token, 'myobjects', local_file, f,
                 content_type="application/octet-stream",
                 response_dict=resp)
    f.close()
    status = resp.get('status')
    assert (status == 200 or status == 201)


def put_dependency(url, token, local_path_to_dep, dep_name):
    metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1'}
    f = open('%s/%s' % (local_path_to_dep, dep_name), 'r')
    content_length = None
    response = dict()
    c.put_object(url, token, 'dependency', dep_name, f,
                 content_length, None, None, "application/octet-stream",
                 metadata, None, None, None, response)
    f.close()
    status = response.get('status')
    assert (status == 200 or status == 201)

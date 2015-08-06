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

import sys

from swiftclient import client as c


def progress():
    sys.stdout.write('.')
    sys.stdout.flush()


def progress_ln():
    sys.stdout.write('\n')
    sys.stdout.flush()


def progress_msg(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()

'''------------------------------------------------------------------------'''


def enable_account_for_storlets(url, token):
    headers = dict()
    headers['X-Account-Meta-storlet-enabled'] = 'True'
    c.post_account(url, token, headers)

'''------------------------------------------------------------------------'''


def put_storlet_containers(url, token):

    response = dict()
    c.put_container(url, token, 'storlet', None, None, response)
    status = response.get('status')
    assert (status >= 200 or status < 300)

    response = dict()
    c.put_container(url, token, 'dependency', None, None, response)
    status = response.get('status')
    assert (status >= 200 or status < 300)

    response = dict()
    c.put_container(url, token, 'storletlog', None, None, response)
    status = response.get('status')
    assert (status >= 200 or status < 300)

'''------------------------------------------------------------------------'''


def put_file_as_storlet_input_object(url, token, local_path, local_file):
    resp = dict()
    f = open('%s/%s' % (local_path, local_file), 'r')
    c.put_object(url, token, 'myobjects', local_file, f,
                 content_type="application/octet-stream",
                 response_dict=resp)
    f.close()
    status = resp.get('status')
    assert (status == 200 or status == 201)

'''------------------------------------------------------------------------'''


def put_storlet_object(url, token, storlet_name, storlet_path,
                       dependency, main_class):
    # Delete previous storlet
    # resp = dict()
    '''try:

        c.delete_object(url, token, 'storlet', storlet_name, None,
                        None, None, None, resp)
    except Exception as e:
        if (resp.get('status')== 404):
            print 'Nothing to delete'
    '''
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

'''------------------------------------------------------------------------'''


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

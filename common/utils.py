
'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2016 All Rights Reserved
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
from swiftclient import client as c


def put_local_file(url, token, container,
                   local_path, local_file,
                   headers=None):
    resp = dict()
    f = open('%s/%s' % (local_path, local_file), 'r')
    c.put_object(url, token, container, local_file, f,
                 headers=headers,
                 content_type="application/octet-stream",
                 response_dict=resp)
    f.close()


def put_storlet_object(url, token, storlet_name, storlet_path,
                       dependency, main_class):
    headers = {'X-Object-Meta-Storlet-Language': 'Java',
               'X-Object-Meta-Storlet-Interface-Version': '1.0',
               'X-Object-Meta-Storlet-Dependency': dependency,
               'X-Object-Meta-Storlet-Object-Metadata': 'no',
               'X-Object-Meta-Storlet-Main': main_class}
    put_local_file(url, token, 'storlet', storlet_path, storlet_name, headers)


def put_storlet_executable_dependencies(url, token, deps):
    resp = dict()
    for d in deps:
        headers = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                   'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}

        f = open('%s' % d, 'r')
        c.put_object(url, token, 'dependency', os.path.basename(d), f,
                     content_type="application/octet-stream",
                     headers=headers,
                     response_dict=resp)
        f.close()
        status = resp.get('status')
        assert (status == 200 or status == 201)


def deploy_storlet(url, token, storlet_jar,
                   storlet_main_class,
                   dependencies):
    # No need to create containers every time
    # put_storlet_containers(url, token)
    put_storlet_object(url, token,
                       os.path.basename(storlet_jar),
                       os.path.dirname(storlet_jar),
                       ','.join(os.path.basename(x) for x in dependencies),
                       storlet_main_class)

    put_storlet_executable_dependencies(url, token, dependencies)


def storlet_get_auth(conf):
    auth_ip = conf['auth_ip']
    auth_port = conf['auth_port']
    account = conf['account']
    user = conf['user_name']
    passwd = conf['password']
    os_options = {'tenant_name': account}
    if conf['region']:
        os_options['region_name'] = conf['region']
    url, token = c.get_auth('http://' + auth_ip + ":" +
                            auth_port + '/v2.0',
                            account + ':' + user,
                            passwd,
                            os_options=os_options,
                            auth_version='2.0')
    return url, token

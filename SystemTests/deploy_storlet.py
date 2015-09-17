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
from swiftclient import client as c
from sys_test_params import ACCOUNT
from sys_test_params import AUTH_IP
from sys_test_params import AUTH_PORT
from sys_test_params import PASSWORD
from sys_test_params import USER_NAME

from storlets_test_utils import put_storlet_object

import sys
import zipfile


def put_storlet_executable_dependencies(url, token, dependency_jars):
    resp = dict()
    for d in dependency_jars:
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                    'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}

        f = open('%s' % d, 'r')
        c.put_object(url, token, 'dependency', os.path.basename(d), f,
                     content_type="application/octet-stream",
                     headers=metadata,
                     response_dict=resp)
        f.close()
        status = resp.get('status')
        assert (status == 200 or status == 201)


def deploy_storlet(url, token, storlet_jar, storlet_main_class,
                   dependency_jars, dependencies):
    # No need to create containers every time
    # put_storlet_containers(url, token)
    put_storlet_object(url, token,
                       os.path.basename(storlet_jar),
                       os.path.dirname(storlet_jar),
                       ','.join(str(x) for x in dependencies),
                       storlet_main_class)
    put_storlet_executable_dependencies(url, token, dependency_jars)


def list_classes(storlet_jar):
    z = zipfile.ZipFile(storlet_jar, 'r')
    for f in z.infolist():
        name = f.filename
        if name.endswith(".class"):
            print('\t* ' + name[0:len(name) - 6].replace('/', '.'))
    z.close()


def main():
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth('http://' + AUTH_IP + ":" +
                            AUTH_PORT + '/v2.0',
                            ACCOUNT + ':' + USER_NAME,
                            PASSWORD,
                            os_options=os_options,
                            auth_version='2.0')

    sys.stdout.write("Enter absolute path to storlet jar file: ")
    storlet_jar = sys.stdin.readline().rstrip()
    print("Your jar file contains the following classes:")
    list_classes(storlet_jar)
    sys.stdout.write("Please enter fully qualified storlet main class " +
                     "(choose from the list above): ")
    storlet_main_class = sys.stdin.readline().rstrip()
    print("Please enter dependency jars (leave a blank line when you are "
          "done):")
    dependency_jars = []
    dependencies = []
    dependency_jar = sys.stdin.readline().rstrip()
    while dependency_jar:
        dependency_jars.append(dependency_jar)
        dependencies.append(os.path.basename(dependency_jar))
        dependency_jar = sys.stdin.readline().rstrip()

    deploy_storlet(url, token, storlet_jar, storlet_main_class,
                   dependency_jars, dependencies)

if __name__ == "__main__":
    main()

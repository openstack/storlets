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

from storlets_test_utils import put_storlet_object
from swiftclient import client as c
from sys_test_params import ACCOUNT
from sys_test_params import AUTH_IP
from sys_test_params import AUTH_PORT
from sys_test_params import PASSWORD
from sys_test_params import USER_NAME

EXECDEP_PATH_TO_BUNDLE = '../StorletSamples/ExecDepStorlet/bin/'
EXECDEP_STORLET_NAME = 'execdepstorlet-1.0.jar'
EXECDEP_STORLET_LOG_NAME = 'execdepstorlet-1.0.log'
EXECDEP_JUNK_FILE = 'junk.txt'
EXECDEP_DEPS_NAMES = ['get42']

'''------------------------------------------------------------------------'''


def put_storlet_dependency(url, token, dependency_name,
                           local_path_to_dependency):
    metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1'}

    f = open('%s/%s' % (local_path_to_dependency, dependency_name), 'r')
    content_length = None
    response = dict()
    c.put_object(url, token, 'dependency', dependency_name, f,
                 content_length, None, None, "application/octet-stream",
                 metadata, None, None, None, response)
    f.close()
    status = response.get('status')
    assert (status == 200 or status == 201)

'''------------------------------------------------------------------------'''


def put_storlet_input_object(url, token):
    resp = dict()
    f = open('%s/%s' % (EXECDEP_PATH_TO_BUNDLE, EXECDEP_JUNK_FILE), 'r')
    c.put_object(url, token, 'myobjects', EXECDEP_JUNK_FILE, f,
                 content_type="application/octet-stream",
                 response_dict=resp)
    f.close()
    status = resp.get('status')
    assert (status == 200 or status == 201)

'''------------------------------------------------------------------------'''


def deploy_storlet(url, token, name, jarName):
    # No need to create containers every time
    # put_storlet_containers(url, token)
    put_storlet_object(url, token, jarName,
                       '../StorletSamples/' + name + '/bin/',
                       '',
                       'com.ibm.storlet.' + name.lower() + '.' + name)

'''------------------------------------------------------------------------'''


def invoke_storlet(url, token, storletName, jarName, objectName, mode):
    resp = dict()
    if mode == 'PUT':
        f = open('../StorletSamples/' + storletName + '/sampleData.txt', 'r')
        c.put_object(url, token, 'myobjects', objectName, f,
                     headers={'X-Run-Storlet': jarName},
                     response_dict=resp)
        f.close()
    if mode == 'GET':
        resp_headers, saved_content = \
            c.get_object(url, token, 'myobjects', objectName,
                         headers={'X-Run-Storlet': jarName},
                         response_dict=resp)

    assert (resp['status'] == 200 or resp['status'] == 201)

    if mode == 'GET':
        return resp_headers, saved_content

'''------------------------------------------------------------------------'''


def main():
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth('http://' + AUTH_IP + ":"
                            + AUTH_PORT + '/v2.0',
                            ACCOUNT + ':' + USER_NAME,
                            PASSWORD,
                            os_options=os_options,
                            auth_version='2.0')

    print('Deploying ReadHeaders storlet')
    deploy_storlet(url, token, 'ReadHeadersStorlet',
                   'readheadersstorlet-1.0.jar')

    print('Deploying ReadHeaders dependency')
    put_storlet_dependency(url, token, 'json-simple-1.1.1.jar',
                           '../StorletSamples/ReadHeadersStorlet/lib')

    print('Deploying CSS storlet')
    deploy_storlet(url, token, 'CssStorlet', 'cssstorlet-1.0.jar')

    print("Invoking CSS storlet in PUT mode")
    invoke_storlet(url, token, 'CssStorlet', 'cssstorlet-1.0.jar',
                   'testDataCss', 'PUT')

    print("Invoking ReadHeaders storlet in GET mode")
    headers, content = invoke_storlet(url, token, 'ReadHeadersStorlet',
                                      'readheadersstorlet-1.0.jar',
                                      'testDataCss', 'GET')

    assert '{"Square-Sums":"[2770444.6455999985, 1.9458262030000027E7,' \
        + ' 95.17999999999981]","Lines-Num":"356","Sums":"[27037.0' \
        + '40000000008, 83229.09999999998, 168.39999999999947]"}' \
        == content

    print("ReadHeaders test finished")
'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main()

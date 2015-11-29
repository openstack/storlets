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
from __init__ import put_file_as_storlet_input_object
from __init__ import put_storlet_object
from __init__ import USER_NAME
from swiftclient import client as c
import unittest

EXECDEP_PATH_TO_BUNDLE = '../../StorletSamples/ExecDepStorlet/bin/'
EXECDEP_STORLET_NAME = 'execdepstorlet-1.0.jar'
EXECDEP_STORLET_LOG_NAME = 'execdepstorlet-1.0.log'
EXECDEP_JUNK_FILE = 'junk.txt'
EXECDEP_DEPS_NAMES = ['get42']


class TestExexDepStorlet(unittest.TestCase):
    def setUp(self):
        os_options = {'tenant_name': ACCOUNT}
        self.url, self.token = c.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT
                                          + "/v2.0", ACCOUNT + ":" + USER_NAME,
                                          PASSWORD, os_options=os_options,
                                          auth_version="2.0")

    def put_storlet_executable_dependencies(self):
        resp = dict()
        for d in EXECDEP_DEPS_NAMES:
            metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                        'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}

            f = open('%s/%s' % (EXECDEP_PATH_TO_BUNDLE, d), 'r')
            c.put_object(self.url, self.token, 'dependency', d, f,
                         content_type="application/octet-stream",
                         headers=metadata,
                         response_dict=resp)
            f.close()
            status = resp.get('status')
            assert (status == 200 or status == 201)

    def deploy_storlet(self):
        # No need to create containers every time
        # put_storlet_containers(url, token)
        put_storlet_object(self.url, self.token,
                           EXECDEP_STORLET_NAME,
                           EXECDEP_PATH_TO_BUNDLE,
                           ','.join(str(x) for x in EXECDEP_DEPS_NAMES),
                           'com.ibm.storlet.execdep.ExecDepStorlet')
        self.put_storlet_executable_dependencies()
        put_file_as_storlet_input_object(self.url,
                                         self.token,
                                         EXECDEP_PATH_TO_BUNDLE,
                                         EXECDEP_JUNK_FILE)

    def invoke_storlet(self):
        metadata = {'X-Run-Storlet': EXECDEP_STORLET_NAME}
        resp = dict()
        resp_headers, gf = c.get_object(self.url, self.token,
                                        'myobjects',
                                        EXECDEP_JUNK_FILE,
                                        response_dict=resp,
                                        headers=metadata)

        assert 'x-object-meta-depend-ret-code' in resp_headers
        assert resp_headers['x-object-meta-depend-ret-code'] == '42'
        assert resp['status'] == 200

    def test_execdep(self):
        self.deploy_storlet()
        self.invoke_storlet()

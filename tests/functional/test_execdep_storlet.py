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

from swiftclient import client as c
from __init__ import StorletFunctionalTest


class TestExecDepStorlet(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'ExecDepStorlet'
        self.storlet_name = 'execdepstorlet-1.0.jar'
        self.storlet_main = 'com.ibm.storlet.execdep.ExecDepStorlet'
        self.storlet_log = 'execdepstorlet-1.0.log'
        self.headers = None
        self.storlet_file = 'junk.txt'
        self.container = 'myobjects'
        self.dep_names = ['get42']
        super(TestExecDepStorlet, self).setUp()

    def test_execdep(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        resp = dict()
        resp_headers, gf = c.get_object(self.url, self.token,
                                        'myobjects',
                                        self.storlet_file,
                                        response_dict=resp,
                                        headers=headers)

        self.assertTrue('x-object-meta-depend-ret-code' in resp_headers)
        self.assertTrue(resp_headers['x-object-meta-depend-ret-code'] == '42')
        self.assertEqual(resp['status'], 200)

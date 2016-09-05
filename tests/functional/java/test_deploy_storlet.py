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

import pexpect
from tests.functional import StorletBaseFunctionalTest, PATH_TO_STORLETS
from tests.functional.java import BIN_DIR


class TestExecDepStorlet(StorletBaseFunctionalTest):
    def setUp(self):
        super(TestExecDepStorlet, self).setUp()
        self.deploy_storlet_path = '../../tools/deploy_storlet.py'
        self.execdep_storlet_path = '%s/java/%s/%s' % (PATH_TO_STORLETS,
                                                       'ExecDepStorlet',
                                                       BIN_DIR)
        self.execdep_storlet_jar_file = '%s/%s' % (self.execdep_storlet_path,
                                                   'execdepstorlet-1.0.jar')
        self.execdep_storlet_dep_file = '%s/%s' % (self.execdep_storlet_path,
                                                   'get42')

        self.timeout = 2

    def test_deploy_storlet_util(self):
        child = pexpect.spawn('python %s %s' % (self.deploy_storlet_path,
                                                self.conf_file))
        try:
            child.expect('Enter absolute path to storlet jar file.*:',
                         timeout=self.timeout)
            child.sendline(self.execdep_storlet_jar_file)
            child.expect('org.openstack.storlet.execdep.ExecDepStorlet',
                         timeout=self.timeout)
            child.expect('Please enter fully qualified storlet main class.*',
                         timeout=self.timeout)
            child.sendline('org.openstack.storlet.execdep.ExecDepStorlet')
            child.expect('Please enter dependency.*', timeout=2)
            child.sendline(self.execdep_storlet_dep_file)
            child.sendline('\n')
            child.expect('Storlet deployment complete.*', timeout=self.timeout)
        except Exception as err:
            self.fail('Unexpected exception %s' % err)

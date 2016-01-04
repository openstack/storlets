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

import unittest
import pexpect
from __init__ import PATH_TO_STORLETS, BIN_DIR

DEPLOY_STORLET_PATH = '../../common/deploy_storlet.py'
CONF_PATH = '../../cluster_config.json'
EXECDEP_STORLET_PATH = '%s/%s/%s' % (PATH_TO_STORLETS,
                                     'ExecDepStorlet',
                                     BIN_DIR)
EXECDEP_STORLET_PATH = '%s/%s' % (EXECDEP_STORLET_PATH,
                                  'execdepstorlet-1.0.jar')
EXECDEP_STORLET_DEP_PATH = '%s/%s' % (EXECDEP_STORLET_PATH,
                                      'get42')


class TestExecDepStorlet(unittest.TestCase):

    def test_deploy_storlet_util(self):
        child = pexpect.spawn('python %s %s' % (DEPLOY_STORLET_PATH,
                                                CONF_PATH))
        try:
            child.expect('Enter absolute path to storlet jar file.*:',
                         timeout=1)
            child.sendline(EXECDEP_STORLET_PATH)
            child.expect('com.ibm.storlet.execdep.ExecDepStorlet',
                         timeout=1)
            child.expect('Please enter fully qualified storlet main class.*',
                         timeout=1)
            child.sendline('com.ibm.storlet.execdep.ExecDepStorlet')
            child.expect('Please enter dependency.*', timeout=1)
            child.sendline(EXECDEP_STORLET_DEP_PATH)
            child.expect('\n')
        except Exception as err:
            self.fail('Unexpected exception %s' % err)

# Copyright IBM Corp. 2015, 2015 All Rights Reserved
# Copyright (c) 2010-2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest
from storlets.tools import deploy_storlet
from tests.functional import StorletBaseFunctionalTest, PATH_TO_STORLETS
from tests.functional.java import BIN_DIR
from tests.functional.common.mixins import DeployTestMixin, EXPECT, SEND_LINE


class TestDeployStorlet(DeployTestMixin, StorletBaseFunctionalTest):
    def setUp(self):
        super(TestDeployStorlet, self).setUp()
        self.deploy_storlet_path = os.path.abspath(deploy_storlet.__file__)
        self.execdep_storlet_path = os.path.join(PATH_TO_STORLETS,
                                                 'java',
                                                 'ExecDepStorlet',
                                                 BIN_DIR)
        self.execdep_storlet_file = os.path.join(self.execdep_storlet_path,
                                                 'execdepstorlet-1.0.jar')
        self.execdep_storlet_dep_file = os.path.join(self.execdep_storlet_path,
                                                     'get42')

        self.scenario = [
            ('Enter storlet language (java or python): ', EXPECT),
            ('java', SEND_LINE),
            ('Enter absolute path to storlet jar file: ', EXPECT),
            (self.execdep_storlet_file, SEND_LINE),
            ('Your jar file contains the following classes:', EXPECT),
            ('\t* org.openstack.storlet.execdep.ExecDepStorlet', EXPECT),
            ('Please enter fully qualified storlet main class '
             '(choose from the list above): ', EXPECT),
            ('org.openstack.storlet.execdep.ExecDepStorlet', SEND_LINE),
            ('Please enter dependency files '
             '(leave a blank line when you are done): ', EXPECT),
            (self.execdep_storlet_dep_file, SEND_LINE),
            ('', SEND_LINE),  # DO NOT send \n but just empty due to sendline
            ('Storlet deployment complete', EXPECT),
        ]


if __name__ == '__main__':
    unittest.main()

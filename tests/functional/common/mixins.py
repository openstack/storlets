# Copyright (c) 2016 OpenStack Foundation.
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

import pexpect
import swiftclient
import os
import hashlib
from storlets.tools.cluster_config_parser import ClusterConfig
from storlets.tools.utils import get_auth

EXPECT = 'expect'
SEND_LINE = 'sendline'


class DeployTestMixin(object):
    def assertUploadedFile(self, container, file_path):
        # Make sure the existence in the swift inside
        conf = ClusterConfig(self.conf_file)
        url, token = get_auth(conf, conf.admin_user, conf.admin_password)

        expected_file = os.path.basename(file_path)
        resp_headers = swiftclient.client.head_object(
            url, token, container, expected_file)
        hasher = hashlib.md5()
        with open(file_path) as f:
            hasher.update(f.read())
        self.assertEqual(resp_headers['etag'], hasher.hexdigest())

    def test_deploy_storlet(self):
        child = pexpect.spawn('python %s %s' % (self.deploy_storlet_path,
                                                self.conf_file))
        try:
            for message, command in self.scenario:
                # FIXME(kota_): i don't get yet why the *expect* call stack
                #               stdout from print function but it seems safe
                #               to assert the output by hand rather than using
                #               expect method
                if command == EXPECT:
                    line = child.readline()
                    self.assertEqual(message.strip(), line.strip())
                elif command == SEND_LINE:
                    child.sendline(message)
                    line = child.readline()
                    self.assertEqual(message.strip(), line.strip())
                else:
                    self.fail("Unexpected scenario found %s, %s"
                              % (message, command))
        except pexpect.EOF as err:
            self.fail(
                'Expected message "%s" not found: %s' % (message, err))

        # Make sure the existence in the swift inside
        # for storlet app
        self.assertUploadedFile('storlet', self.execdep_storlet_file)
        # for dependency
        self.assertUploadedFile('dependency', self.execdep_storlet_dep_file)

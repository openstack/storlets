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

from swiftclient import client as c
from tests.functional.java import StorletJavaFunctionalTest
import unittest


class TestExecDepStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = 'execdepstorlet-1.0.log'
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.execdep.ExecDepStorlet'
        super(TestExecDepStorlet, self).setUp('ExecDepStorlet',
                                              'execdepstorlet-1.0.jar',
                                              main_class,
                                              'junk.txt',
                                              ['get42'])

    def test_execdep(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        resp = dict()
        resp_headers, gf = c.get_object(self.url, self.token,
                                        self.container,
                                        self.storlet_file,
                                        response_dict=resp,
                                        headers=headers)

        self.assertIn('x-object-meta-depend-ret-code', resp_headers)
        self.assertEqual('42', resp_headers['x-object-meta-depend-ret-code'])
        self.assertEqual(200, resp['status'])


class TestExecDepStorletOnProxy(TestExecDepStorlet):
    def setUp(self):
        super(TestExecDepStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

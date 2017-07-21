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


class TestMetadataStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = 'testmetadatastorlet-1.0.log'
        headers = {'X-Object-Meta-key1': '1',
                   'X-Object-Meta-key2': '2',
                   'X-Object-Meta-key3': '3',
                   'X-Object-Meta-key4': '4',
                   'X-Object-Meta-key5': '5',
                   'X-Object-Meta-key6': '6',
                   'X-Object-Meta-key7': '7',
                   'X-Object-Meta-key8': '8',
                   'X-Object-Meta-key9': '9',
                   'X-Object-Meta-key10': '10'}
        self.additional_headers = {}
        main_class = ('org.openstack.storlet.testmetadatastorlet'
                      '.MetadataStorlet')
        super(TestMetadataStorlet, self).setUp('TestMetadataStorlet',
                                               'testmetadatastorlet-1.0.jar',
                                               main_class,
                                               'source.txt',
                                               headers=headers)

    def test_metadata_get(self, params=None, global_params=None):
        if params is not None:
            querystring = ''
            for key in params:
                querystring += '%s=%s,' % (key, params[key])
            querystring = querystring[:-1]
        else:
            querystring = None

        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        original_headers, original_content = \
            c.get_object(self.url, self.token,
                         self.container, self.storlet_file,
                         response_dict=dict(), headers=headers)
        self.assertEqual('1', original_headers['X-Object-Meta-key1'.lower()])
        self.assertEqual('2', original_headers['X-Object-Meta-key2'.lower()])
        self.assertEqual('3', original_headers['X-Object-Meta-key3'.lower()])
        self.assertEqual('4', original_headers['X-Object-Meta-key4'.lower()])
        self.assertEqual('5', original_headers['X-Object-Meta-key5'.lower()])
        self.assertEqual('6', original_headers['X-Object-Meta-key6'.lower()])
        self.assertEqual('7', original_headers['X-Object-Meta-key7'.lower()])
        self.assertEqual('8', original_headers['X-Object-Meta-key8'.lower()])
        self.assertEqual('9', original_headers['X-Object-Meta-key9'.lower()])
        self.assertEqual('10', original_headers['X-Object-Meta-key10'.lower()])
        omv = original_headers['X-Object-Meta-override_key'.lower()]
        self.assertEqual('new_value', omv)


class TestMetadataStorletOnProxy(TestMetadataStorlet):
    def setUp(self):
        super(TestMetadataStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

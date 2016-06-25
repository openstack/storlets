'''----------------------------------------------------------------
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
----------------------------------------------------------------'''

from swiftclient import client as c
from __init__ import StorletFunctionalTest


class TestMetadataStorlet(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'TestMetadataStorlet'
        self.storlet_name = 'testmetadatastorlet-1.0.jar'
        self.storlet_main = ('com.ibm.storlet.testmetadatastorlet'
                             '.MetadataStorlet')
        self.storlet_log = 'testmetadatastorlet-1.0.log'
        self.headers = {'X-Object-Meta-key1': '1',
                        'X-Object-Meta-key2': '2',
                        'X-Object-Meta-key3': '3',
                        'X-Object-Meta-key4': '4',
                        'X-Object-Meta-key5': '5',
                        'X-Object-Meta-key6': '6',
                        'X-Object-Meta-key7': '7',
                        'X-Object-Meta-key8': '8',
                        'X-Object-Meta-key9': '9',
                        'X-Object-Meta-key10': '10'}
        self.storlet_file = 'source.txt'
        self.container = 'myobjects'
        self.dep_names = []
        self.additional_headers = {}
        super(TestMetadataStorlet, self).setUp()

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
                         'myobjects', self.storlet_file,
                         response_dict=dict(), headers=headers)
        self.assertEqual(original_headers['X-Object-Meta-key1'.lower()], '1')
        self.assertEqual(original_headers['X-Object-Meta-key2'.lower()], '2')
        self.assertEqual(original_headers['X-Object-Meta-key3'.lower()], '3')
        self.assertEqual(original_headers['X-Object-Meta-key4'.lower()], '4')
        self.assertEqual(original_headers['X-Object-Meta-key5'.lower()], '5')
        self.assertEqual(original_headers['X-Object-Meta-key6'.lower()], '6')
        self.assertEqual(original_headers['X-Object-Meta-key7'.lower()], '7')
        self.assertEqual(original_headers['X-Object-Meta-key8'.lower()], '8')
        self.assertEqual(original_headers['X-Object-Meta-key9'.lower()], '9')
        self.assertEqual(original_headers['X-Object-Meta-key10'.lower()], '10')
        omv = original_headers['X-Object-Meta-override_key'.lower()]
        self.assertEqual(omv, 'new_value')


class TestMetadataStorletOnProxy(TestMetadataStorlet):
    def setUp(self):
        super(TestMetadataStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}

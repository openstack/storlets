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


class TestCompressStorlet(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'CompressStorlet'
        self.storlet_name = 'compressstorlet-1.0.jar'
        self.storlet_main = 'org.openstack.storlet.compress.CompressStorlet'
        self.storlet_log = ''
        self.headers = {}
        self.storlet_file = 'input.txt'
        self.container = 'myobjects'
        self.dep_names = []
        self.additional_headers = {}
        super(TestCompressStorlet, self).setUp()

    def test_put(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        querystring = "action=compress"

        with open('../../StorletSamples/CompressStorlet/bin/input.txt',
                  'r') as myfile:
            data = myfile.read()

        response = dict()
        c.put_object(self.url, self.token, self.container, self.storlet_file,
                     data, None, None, None,
                     "application/octet-stream", headers, None, None,
                     querystring, response)

        querystring = "action=uncompress"

        original_headers, original_content = \
            c.get_object(self.url, self.token, self.container,
                         self.storlet_file,
                         response_dict=dict())

        object_length = int(original_headers['content-length'])

        self.assertLess(object_length, len(data))

        processed_headers, returned_content = \
            c.get_object(self.url, self.token, self.container,
                         self.storlet_file,
                         query_string=querystring, response_dict=dict(),
                         headers=headers, resp_chunk_size=object_length)
        processed_content = ''
        for chunk in returned_content:
            if chunk:
                processed_content += chunk

        self.assertEqual(data, processed_content)


class TestCompressStorletOnProxy(TestCompressStorlet):
    def setUp(self):
        super(TestCompressStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}

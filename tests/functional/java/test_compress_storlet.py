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


class TestCompressStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = ''
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.compress.CompressStorlet'
        super(TestCompressStorlet, self).setUp('CompressStorlet',
                                               'compressstorlet-1.0.jar',
                                               main_class,
                                               'input.txt')

    def test_put(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        querystring = "action=compress"

        # simply set 1KB string data to compress
        data = 'A' * 1024

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


if __name__ == '__main__':
    unittest.main()

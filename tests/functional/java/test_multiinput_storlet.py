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
from hashlib import md5


class TestMultiInputStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.additional_headers = {}
        super(TestMultiInputStorlet, self).setUp(
            storlet_dir='MultiInputStorlet',
            storlet_name='multiinputstorlet-1.0.jar',
            storlet_main='org.openstack.storlet.multiinput.MultiInputStorlet',
            storlet_file=None,
            headers={})

    def test_get_extra_sources(self):
        obj = 'small'
        obj2 = 'small2'
        c.put_object(self.url, self.token,
                     self.container, obj,
                     '0123456789abcd')
        c.put_object(self.url, self.token,
                     self.container, obj2,
                     'efghijklmnopqr')

        headers = {
            'X-Run-Storlet': self.storlet_name,
            'X-Storlet-Extra-Resources':
            '/%s/%s' % (self.container, obj2),
            'X-Storlet-Run-On-Proxy': ''
        }
        headers.update(self.additional_headers)

        resp_headers, resp_content = c.get_object(
            self.url, self.token, self.container, obj,
            headers=headers)
        self.assertEqual('0123456789abcdefghijklmnopqr',
                         resp_content)

    def test_put_x_copy_from_extra_sources(self):
        obj = 'small'
        obj2 = 'small2'
        copied_obj = 'copied'
        c.put_object(self.url, self.token,
                     self.container, obj,
                     '0123456789abcd',
                     headers={'X-Object-Meta-Key1': 'value1'})
        c.put_object(self.url, self.token,
                     self.container, obj2,
                     'efghijklmnopqr',
                     headers={'X-Object-Meta-Key2': 'value2'})

        headers = {
            'X-Run-Storlet': self.storlet_name,
            'X-Copy-From':
            '/%s/%s' % (self.container, obj),
            'X-Storlet-Extra-Resources':
            '/%s/%s' % (self.container, obj2),
        }
        headers.update(self.additional_headers)

        expected_string = '0123456789abcdefghijklmnopqr'
        etag = c.put_object(
            self.url, self.token, self.container, copied_obj,
            headers=headers)

        hasher = md5()
        hasher.update(expected_string)

        self.assertEqual(hasher.hexdigest(), etag)

        resp_headers, resp_content = c.get_object(
            self.url, self.token, self.container, copied_obj)
        self.assertEqual(expected_string, resp_content)
        self.assertEqual('value1', resp_headers['x-object-meta-key1'])
        self.assertEqual('value2', resp_headers['x-object-meta-key2'])


class TestMultiInputStorletOnProxy(TestMultiInputStorlet):
    def setUp(self):
        super(TestMultiInputStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

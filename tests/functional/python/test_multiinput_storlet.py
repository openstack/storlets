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
from swiftclient import client as c
from tests.functional.python import StorletPythonFunctionalTest
import unittest
from hashlib import md5


class TestMultiInputStorlet(StorletPythonFunctionalTest):
    def setUp(self):
        self.additional_headers = {}
        super(TestMultiInputStorlet, self).setUp(
            storlet_dir='multi_input',
            storlet_name='multi_input.py',
            storlet_main='multi_input.MultiInputStorlet',
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
            os.path.join('/' + self.container, obj2)
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
            os.path.join('/' + self.container, obj),
            'X-Storlet-Extra-Resources':
            os.path.join('/' + self.container, obj2),
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


class TestMultiInputMIMEStorlet(StorletPythonFunctionalTest):
    def setUp(self):
        self.additional_headers = {}
        super(TestMultiInputMIMEStorlet, self).setUp(
            storlet_dir='multi_input',
            storlet_name='multi_input_mime.py',
            storlet_main='multi_input_mime.MultiInputMIMEStorlet',
            storlet_file=None,
            headers={})

    def test_get_multipart_mime_response(self):
        obj = 'small'
        obj2 = 'small2'
        body = '0123456789abcd'
        body2 = 'efghijklmnopqr'
        c.put_object(self.url, self.token,
                     self.container, obj, body)
        c.put_object(self.url, self.token,
                     self.container, obj2, body2)

        headers = {
            'X-Run-Storlet': self.storlet_name,
            'X-Storlet-Extra-Resources':
            os.path.join('/' + self.container, obj2)
        }
        headers.update(self.additional_headers)

        resp_headers, resp_content = c.get_object(
            self.url, self.token, self.container, obj,
            headers=headers)

        multipart_prefix = 'multipart/mixed; boundary='
        # N.B. swiftclient makes the header key as lower case
        self.assertIn('content-type', resp_headers)
        self.assertIn(
            multipart_prefix, resp_headers['content-type'])
        boundary = resp_headers['content-type'][len(multipart_prefix):]

        self.assertEqual(
            '%s\n--%s\n%s\n--%s--' % (body, boundary, body2, boundary),
            resp_content)


class TestMultiInputMIMEStorletOnProxy(TestMultiInputMIMEStorlet):
    def setUp(self):
        super(TestMultiInputMIMEStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

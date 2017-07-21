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

import threading
from swiftclient import client as swift_client
from swiftclient import ClientException
from nose.plugins.attrib import attr
from storlets.tools.utils import get_member_auth
from tests.functional.java import StorletJavaFunctionalTest
import unittest


class myTestThread (threading.Thread):
    def __init__(self, url, token, test_class):
        threading.Thread.__init__(self)
        self.token = token
        self.url = url
        self.test_class = test_class

    def run(self):
        self.test_class.invokeTestStorlet("print", False)


class TestTestStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = ''
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.test.test1'
        super(TestTestStorlet, self).setUp('TestStorlet',
                                           'test-10.jar',
                                           main_class,
                                           '')

        self.member_url, self.member_token = get_member_auth(self.conf)

        swift_client.put_object(self.url,
                                self.token,
                                self.container,
                                'test_object',
                                'some content')

    def invokeTestStorlet(self, op, withlog=False):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        if withlog is True:
            headers['X-Storlet-Generate-Log'] = 'True'

        params = 'op={0}&param2=val2'.format(op)
        resp_dict = dict()
        try:
            resp_headers, gf = swift_client.get_object(self.url, self.token,
                                                       self.container,
                                                       'test_object',
                                                       None, None, params,
                                                       resp_dict, headers)
            get_text = gf
            get_response_status = resp_dict.get('status')

            if withlog is True:
                resp_headers, gf = swift_client.get_object(self.url,
                                                           self.token,
                                                           'storletlog',
                                                           'test.log',
                                                           None, None,
                                                           None, None,
                                                           headers)
                self.assertEqual(200, resp_headers.get('status'))
                gf.read()
                self.assertEqual(resp_headers.get('status') == 200)

            if op == 'print':
                self.assertEqual(200, get_response_status)
                self.assertIn('op', get_text)
                self.assertIn('print', get_text)
                self.assertIn('param2', get_text)
                self.assertIn('val2', get_text)

        except Exception:
            get_response_status = resp_dict.get('status')
            if op == 'crash':
                self.assertTrue(get_response_status >= 500 or
                                get_response_status == 404)

    def test_print(self):
        self.invokeTestStorlet("print", False)

    def test_crash(self):
        self.invokeTestStorlet("crash")

    @attr('slow')
    def test_hold(self):
        self.invokeTestStorlet("hold")

    def invokeTestStorletinParallel(self):
        mythreads = []

        for i in range(10):
            new_thread = myTestThread(self.url, self.token, self)
            mythreads.append(new_thread)

        for t in mythreads:
            t.start()

        for t in mythreads:
            t.join()

    @attr('slow')
    def test_parallel_print(self):
        self.invokeTestStorletinParallel()

    def test_storlet_acl_get_fail(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        exc_pattern = '^.*403 Forbidden.*$'
        with self.assertRaisesRegexp(ClientException, exc_pattern):
            swift_client.get_object(self.member_url, self.member_token,
                                    self.container, 'test_object',
                                    headers=headers)

    def test_storlet_acl_get_success(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        exc_pattern = '^.*403 Forbidden.*$'
        with self.assertRaisesRegexp(ClientException, exc_pattern):
            swift_client.get_object(self.member_url, self.member_token,
                                    self.container, 'test_object',
                                    headers=headers)

        headers = {'X-Storlet-Container-Read': self.conf.member_user,
                   'X-Storlet-Name': self.storlet_name}
        swift_client.post_container(self.url,
                                    self.token,
                                    self.container,
                                    headers)
        swift_client.head_container(self.url,
                                    self.token,
                                    self.container)
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        resp_dict = dict()
        swift_client.get_object(self.member_url,
                                self.member_token,
                                self.container, 'test_object',
                                response_dict=resp_dict,
                                headers=headers)
        self.assertEqual(200, resp_dict['status'])


class TestTestStorletOnProxy(TestTestStorlet):
    def setUp(self):
        super(TestTestStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

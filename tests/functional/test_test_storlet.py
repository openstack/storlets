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

from __init__ import ACCOUNT
from __init__ import AUTH_IP
from __init__ import AUTH_PORT
from __init__ import PASSWORD
from __init__ import put_storlet_object
from __init__ import USER_NAME
import threading
import unittest

from swiftclient import client as c


TEST_STORLET_NAME = 'test-10.jar'
PATH_TO_STORLETS = '../../StorletSamples'


class myTestThread (threading.Thread):
    def __init__(self, url, token, test_class):
        threading.Thread.__init__(self)
        self.token = token
        self.url = url
        self.test_class = test_class

    def run(self):
        self.test_class.invokeTestStorlet("print", False)


class TestTestStorlet(unittest.TestCase):
    def setUp(self):
        os_options = {'tenant_name': ACCOUNT}
        self.url, self.token = c.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT
                                          + "/v2.0", ACCOUNT + ":" + USER_NAME,
                                          PASSWORD, os_options=os_options,
                                          auth_version='2.0')
        put_storlet_object(self.url,
                           self.token,
                           TEST_STORLET_NAME,
                           "%s/TestStorlet/bin" % PATH_TO_STORLETS,
                           '',
                           'com.ibm.storlet.test.test1')
        c.put_object(self.url,
                     self.token,
                     'myobjects',
                     'test_object',
                     'some content')

    def invokeTestStorlet(self, op, withlog=False):
        headers = {'X-Run-Storlet': TEST_STORLET_NAME}
        if withlog is True:
            headers['X-Storlet-Generate-Log'] = 'True'

        params = 'op={0}&param2=val2'.format(op)
        resp_dict = dict()
        try:
            resp_headers, gf = c.get_object(self.url, self.token, 'myobjects',
                                            'test_object', None, None, params,
                                            resp_dict, headers)
            get_text = gf
            get_response_status = resp_dict.get('status')

            if withlog is True:
                resp_headers, gf = c.get_object(self.url, self.token,
                                                'storletlog', 'test.log',
                                                None, None, None, None,
                                                headers)
                assert resp_headers.get('status') == 200
                gf.read()
                assert resp_headers.get('status') == 200

            if op == 'print':
                assert get_response_status == 200
                assert 'op' in get_text
                assert 'print' in get_text
                assert 'param2' in get_text
                assert 'val2' in get_text

        except Exception:
            get_response_status = resp_dict.get('status')
            if op == 'crash':
                assert get_response_status >= 500 or get_response_status == 404

    def test_print(self):
        self.invokeTestStorlet("print", False)

    def test_crash(self):
        self.invokeTestStorlet("crash")

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

    def test_parallel_print(self):
        self.invokeTestStorletinParallel()

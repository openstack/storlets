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

import threading
from swiftclient import client as c
from __init__ import StorletFunctionalTest


class myTestThread (threading.Thread):
    def __init__(self, url, token, test_class):
        threading.Thread.__init__(self)
        self.token = token
        self.url = url
        self.test_class = test_class

    def run(self):
        self.test_class.invokeTestStorlet("print", False)


class TestTestStorlet(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'TestStorlet'
        self.storlet_name = 'test-10.jar'
        self.storlet_main = 'com.ibm.storlet.test.test1'
        self.storlet_log = ''
        self.headers = None
        self.storlet_file = ''
        self.container = 'myobjects'
        self.dep_names = []
        super(TestTestStorlet, self).setUp()

        c.put_object(self.url,
                     self.token,
                     self.container,
                     'test_object',
                     'some content')

    def invokeTestStorlet(self, op, withlog=False):
        headers = {'X-Run-Storlet': self.storlet_name}
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
                self.assertEqual(resp_headers.get('status'), 200)
                gf.read()
                self.assertEqual(resp_headers.get('status') == 200)

            if op == 'print':
                self.assertEqual(get_response_status, 200)
                self.assertTrue('op' in get_text)
                self.assertTrue('print' in get_text)
                self.assertTrue('param2' in get_text)
                self.assertTrue('val2' in get_text)

        except Exception:
            get_response_status = resp_dict.get('status')
            if op == 'crash':
                self.assertTrue(get_response_status >= 500 or
                                get_response_status == 404)

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

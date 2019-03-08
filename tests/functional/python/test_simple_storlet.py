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
import tempfile
from swiftclient import client
from nose.plugins.attrib import attr
from tests.functional.python import StorletPythonFunctionalTest
import unittest
from eventlet.green import urllib2
from storlets.agent.common.utils import DEFAULT_PY3


class TestSimpleStorlet(StorletPythonFunctionalTest):
    def setUp(self, version=None):
        self.storlet_log = 'simple.log'
        self.content = 'abcdefghijklmonp'
        self.additional_headers = {}
        super(TestSimpleStorlet, self).setUp(
            storlet_dir='simple',
            storlet_name='simple.py',
            storlet_main='simple.SimpleStorlet',
            storlet_file='source.txt',
            version=version)

    def test_get(self):
        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name}
        headers, content = client.get_object(
            self.url, self.token, self.container, self.storlet_file,
            response_dict=resp, headers=req_headers)
        self.assertEqual(200, resp['status'])
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content, content)

    def test_range_get(self):
        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name,
                       'X-Storlet-Range': 'bytes=1-4'}
        headers, content = client.get_object(
            self.url, self.token, self.container, self.storlet_file,
            response_dict=resp, headers=req_headers)
        self.assertEqual(200, resp['status'])
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content[1:5], content)

    def test_put(self):
        objname = self.storlet_file + '-put'

        resp = dict()
        req_headers = {'X-Run-Storlet': self.storlet_name}
        client.put_object(
            self.url, self.token, self.container, objname,
            self.content, response_dict=resp, headers=req_headers)
        self.assertEqual(201, resp['status'])

        resp = dict()
        headers, content = client.get_object(
            self.url, self.token, self.container, objname,
            response_dict=resp)
        self.assertEqual(200, resp['status'])
        self.assertEqual('simple', headers['x-object-meta-test'])
        self.assertEqual(self.content, content)

        resp = dict()
        client.delete_object(
            self.url, self.token, self.container, objname,
            response_dict=resp)
        self.assertEqual(204, resp['status'])

    @attr('slow')
    def test_put_512MB_file(self):
        with tempfile.NamedTemporaryFile() as f:
            with open(f.name, 'w') as wf:
                for _ in range(128):
                    wf.write('1' * (4 * 1024 * 1024))

            headers = {'X-Run-Storlet': self.storlet_name}
            headers.update(self.additional_headers)
            with open(f.name, 'r') as rf:
                response = dict()
                client.put_object(self.url, self.token,
                                  self.container, f.name, rf,
                                  512 * 1024 * 1024, None, None,
                                  "application/octet-stream",
                                  headers, None, None, None, response)

            status = response.get('status')
            self.assertEqual(201, status)

    def test_copy_from(self):
        resp = dict()
        objname = self.storlet_file + '-copy'
        req_headers = {'X-Run-Storlet': self.storlet_name,
                       'X-Copy-From': '%s/%s' %
                       (self.container, self.storlet_file)}
        client.put_object(
            self.url, self.token, self.container, objname,
            self.content, response_dict=resp, headers=req_headers)

        self.assertEqual(201, resp['status'])
        resp_header = resp['headers']
        self.assertEqual('%s/%s' % (self.container, self.storlet_file),
                         resp_header['x-storlet-generated-from'])
        self.assertEqual(self.acct,
                         resp_header['x-storlet-generated-from-account'])
        self.assertIn('x-storlet-generated-from-last-modified', resp_header)

        headers = client.head_object(self.url, self.token,
                                     self.container, objname)
        self.assertEqual(str(len(self.content)), headers['content-length'])

        resp = dict()
        client.delete_object(
            self.url, self.token, self.container, objname,
            response_dict=resp)
        self.assertEqual(204, resp['status'])

    def test_copy_dest(self):
        # No COPY in swiftclient. Using urllib instead...
        url = os.path.join(self.url, self.container, self.storlet_file)
        objname = self.storlet_file + '-copy-ex'
        headers = {'X-Auth-Token': self.token,
                   'X-Run-Storlet': self.storlet_name,
                   'Destination': '%s/%s' % (self.container, objname)}
        headers.update(self.additional_headers)
        req = urllib2.Request(url, headers=headers)
        req.get_method = lambda: 'COPY'
        conn = urllib2.urlopen(req, timeout=10)

        self.assertEqual(201, conn.getcode())
        self.assertEqual('%s/%s' % (self.container, self.storlet_file),
                         conn.info()['x-storlet-generated-from'])
        self.assertEqual(self.acct,
                         conn.info()['x-storlet-generated-from-account'])
        self.assertIn('x-storlet-generated-from-last-modified', conn.info())

        headers = client.head_object(self.url, self.token,
                                     self.container, objname)
        self.assertEqual(str(len(self.content)), headers['content-length'])

        resp = dict()
        client.delete_object(
            self.url, self.token, self.container, objname,
            response_dict=resp)
        self.assertEqual(204, resp['status'])


class TestSimpleStorletOnProxy(TestSimpleStorlet):
    def setUp(self):
        super(TestSimpleStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


class TestSimpleStorletRunPy3(TestSimpleStorlet):
    def setUp(self):
        super(TestSimpleStorletRunPy3, self).setUp(version=DEFAULT_PY3)


if __name__ == '__main__':
    unittest.main()

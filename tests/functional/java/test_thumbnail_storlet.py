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
from eventlet.green import urllib2


class TestThumbnailStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = None
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.thumbnail.ThumbnailStorlet'
        super(TestThumbnailStorlet, self).setUp('ThumbnailStorlet',
                                                'thumbnail-1.0.jar',
                                                main_class,
                                                'sample.jpg')

    def invoke_storlet_on_get(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        resp = dict()
        resp_headers, gf = c.get_object(self.url, self.token,
                                        self.container,
                                        self.storlet_file,
                                        response_dict=resp,
                                        headers=headers)
        with open('/tmp/sample.jpg', 'w') as f:
            f.write(gf)

        self.assertIn(resp['status'], [200, 202])

    def invoke_storlet_on_put(self):
        headers = {'X-Run-Storlet': self.storlet_name,
                   'x-object-meta-name': 'thumbnail'}
        headers.update(self.additional_headers)
        resp = dict()
        source_file = '%s/%s' % (self.path_to_bundle, self.storlet_file)
        with open(source_file, 'r') as f:
            c.put_object(self.url, self.token,
                         self.container, 'gen_thumb_on_put.jpg', f,
                         headers=headers,
                         response_dict=resp)

        status = resp.get('status')
        self.assertIn(status, [201, 202])

        headers = c.head_object(self.url, self.token,
                                self.container, 'gen_thumb_on_put.jpg')
        self.assertEqual('49032', headers['content-length'])
        self.assertEqual('thumbnail', headers['x-object-meta-name'])

    def invoke_storlet_on_copy_from(self):
        headers = {'X-Run-Storlet': self.storlet_name,
                   'X-Object-Meta-Name': 'thumbnail',
                   'X-Copy-From': '%s/%s' %
                   (self.container, self.storlet_file)}
        headers.update(self.additional_headers)
        resp = dict()
        c.put_object(self.url, self.token,
                     self.container, 'gen_thumb_on_copy.jpg', '',
                     headers=headers,
                     response_dict=resp)

        status = resp.get('status')
        self.assertIn(status, [201, 202])
        rh = resp['headers']
        self.assertEqual(rh['x-storlet-generated-from'],
                         '%s/%s' %
                         (self.container, self.storlet_file))
        self.assertEqual(rh['x-storlet-generated-from-account'],
                         self.acct)
        self.assertIn('x-storlet-generated-from-last-modified', rh)

        headers = c.head_object(self.url, self.token,
                                self.container, 'gen_thumb_on_copy.jpg')
        self.assertEqual('49032', headers['content-length'])
        self.assertEqual('thumbnail', headers['x-object-meta-name'])
        self.assertTrue('x-object-meta-x-timestamp' not in headers)
        self.assertTrue('x-timestamp' in headers)

    def invoke_storlet_on_copy_dest(self):
        # No COPY in swiftclient. Using urllib instead...
        url = '%s/%s/%s' % (self.url, self.container, self.storlet_file)
        headers = {'X-Auth-Token': self.token,
                   'X-Run-Storlet': self.storlet_name,
                   'X-Object-Meta-Name': 'thumbnail',
                   'Destination': '%s/gen_thumb_on_copy_.jpg' % self.container}
        headers.update(self.additional_headers)
        req = urllib2.Request(url, headers=headers)
        req.get_method = lambda: 'COPY'
        conn = urllib2.urlopen(req, timeout=10)
        status = conn.getcode()
        self.assertIn(status, [201, 202])

        headers = c.head_object(self.url, self.token,
                                self.container, 'gen_thumb_on_copy_.jpg')
        self.assertEqual('49032', headers['content-length'])
        self.assertEqual('thumbnail', headers['x-object-meta-name'])
        self.assertTrue('x-object-meta-x-timestamp' not in headers)
        self.assertTrue('x-timestamp' in headers)

    def test_get(self):
        self.invoke_storlet_on_get()

    def test_put(self):
        self.invoke_storlet_on_put()

    def test_copy_put(self):
        self.invoke_storlet_on_copy_from()

    def test_copy(self):
        self.invoke_storlet_on_copy_dest()


class TestThumbnailStorletOnProxy(TestThumbnailStorlet):
    def setUp(self):
        super(TestThumbnailStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

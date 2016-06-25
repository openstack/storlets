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

from eventlet.green import urllib2


class TestThumbnailStorlet(StorletFunctionalTest):
    def setUp(self):
        self.storlet_dir = 'ThumbnailStorlet'
        self.storlet_name = 'thumbnail-1.0.jar'
        self.storlet_main = 'com.ibm.storlet.thumbnail.ThumbnailStorlet'
        self.storlet_log = None
        self.headers = None
        self.storlet_file = 'sample.jpg'
        self.container = 'myobjects'
        self.dep_names = []
        self.additional_headers = {}
        super(TestThumbnailStorlet, self).setUp()

    def invoke_storlet_on_get(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        resp = dict()
        resp_headers, gf = c.get_object(self.url, self.token,
                                        'myobjects',
                                        self.storlet_file,
                                        response_dict=resp,
                                        headers=headers)
        with open('/tmp/sample.jpg', 'w') as f:
            f.write(gf)

        self.assertTrue(resp['status'] in [200, 202])

    def invoke_storlet_on_put(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        resp = dict()
        source_file = '%s/%s' % (self.path_to_bundle, self.storlet_file)
        with open(source_file, 'r') as f:
            c.put_object(self.url, self.token,
                         'myobjects', 'gen_thumb_on_put.jpg', f,
                         headers=headers,
                         response_dict=resp)

        status = resp.get('status')
        self.assertTrue(status in [201, 202])

        headers = c.head_object(self.url, self.token,
                                'myobjects', 'gen_thumb_on_put.jpg')
        self.assertEqual(headers['content-length'], '49032')

    def invoke_storlet_on_copy_from(self):
        headers = {'X-Run-Storlet': self.storlet_name,
                   'X-Copy-From': 'myobjects/%s' % self.storlet_file}
        headers.update(self.additional_headers)
        resp = dict()
        c.put_object(self.url, self.token,
                     'myobjects', 'gen_thumb_on_copy.jpg', '',
                     headers=headers,
                     response_dict=resp)

        status = resp.get('status')
        self.assertTrue(status in [201, 202])
        rh = resp['headers']
        self.assertEqual(rh['x-storlet-generated-from'],
                         'myobjects/%s' % self.storlet_file)
        self.assertEqual(rh['x-storlet-generated-from-account'],
                         self.acct)
        self.assertTrue('x-storlet-generated-from-last-modified' in rh)

        headers = c.head_object(self.url, self.token,
                                'myobjects', 'gen_thumb_on_copy.jpg')
        self.assertEqual(headers['content-length'], '49032')

    def invoke_storlet_on_copy_dest(self):
        # No COPY in swiftclient. Using urllib instead...
        url = '%s/%s/%s' % (self.url, 'myobjects', self.storlet_file)
        headers = {'X-Auth-Token': self.token,
                   'X-Run-Storlet': self.storlet_name,
                   'Destination': 'myobjects/gen_thumb_on_copy_.jpg'}
        headers.update(self.additional_headers)
        req = urllib2.Request(url, headers=headers)
        req.get_method = lambda: 'COPY'
        conn = urllib2.urlopen(req, timeout=10)
        status = conn.getcode()
        self.assertTrue(status in [201, 202])

        headers = c.head_object(self.url, self.token,
                                'myobjects', 'gen_thumb_on_copy_.jpg')
        self.assertEqual(headers['content-length'], '49032')

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

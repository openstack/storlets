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

import json
import random
import string
from swiftclient import client
from tests.functional.java import StorletJavaFunctionalTest
import unittest


class TestSLO(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = 'identitystorlet-1.0.log'
        self.additional_headers = {}
        self.chunks = []
        main_class = 'org.openstack.storlet.identity.IdentityStorlet'
        super(TestSLO, self).setUp('IdentityStorlet',
                                   'identitystorlet-1.0.jar',
                                   main_class,
                                   '')

        self.create_local_chunks()
        self.put_SLO()

    def create_local_chunks(self):
        for i in range(10):
            self.chunks.append(
                ''.join([random.choice(string.ascii_uppercase + string.digits)
                         for _ in range(1024)]).encode('ascii'))

    def put_SLO(self):
        assembly = []
        for i in range(10):
            oname = 'slo_chunk_%d' % i
            etag = client.put_object(self.url, self.token,
                                     self.container, oname, self.chunks[i],
                                     content_type="application/octet-stream")

            segment = dict()
            segment['path'] = '%s/%s' % (self.container, oname)
            segment['size_bytes'] = 1024
            segment['etag'] = etag
            assembly.append(segment)

        headers = {'x-object-meta-prop1': 'val1'}
        client.put_object(self.url, self.token, self.container,
                          'assembly', json.dumps(assembly),
                          headers=headers,
                          query_string='multipart-manifest=put')

    def compare_slo_to_chunks(self, body):
        length = 0
        for (i, chunk) in enumerate(body):
            self.assertEqual(chunk, self.chunks[i])
            length += 1
        self.assertEqual(length, 10)

    def test_get_SLO_without_storlet(self):
        _, body = client.get_object(self.url, self.token,
                                    self.container, 'assembly',
                                    resp_chunk_size=1024)
        self.compare_slo_to_chunks(body)

    test_get_SLO_without_storlet.slow = 1

    def test_get_SLO_with_storlet(self):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        _, body = client.get_object(self.url, self.token,
                                    self.container, 'assembly',
                                    resp_chunk_size=1024,
                                    headers=headers)
        self.compare_slo_to_chunks(body)

    test_get_SLO_with_storlet.slow = 1


class TestSloOnProxy(TestSLO):
    def setUp(self):
        super(TestSloOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()

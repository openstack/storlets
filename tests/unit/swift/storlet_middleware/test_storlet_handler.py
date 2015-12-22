# Copyright (c) 2010-2015 OpenStack Foundation
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

from os.path import join
from storlet_middleware import storlet_handler
from swift.common.swob import Request
from swift.common.swob import Response
import unittest


DEFAULT_CONFIG = {
    'storlet_container': 'storlet',
    'storlet_dependency': 'dependency',
    'storlet_timeout': '40',
    'storlet_gateway_module':
        'storlet_gateway.storlet_stub_gateway:StorletStubBase',
    'storlet_gateway_conf': '/etc/swift/storlet_stub_gateway.conf',
    'execution_server': 'proxy'}


class FakeApp(object):
    def __call__(self, env, start_response):
        req = Request(env)
        return Response(request=req, body='FAKE APP')(
            env, start_response)


class TestStorletsHandler(unittest.TestCase):
    def setUp(self):
        self.got_statuses = []

    def tearDown(self):
        pass

    def get_app(self, app, global_conf, **local_conf):
        factory = storlet_handler.filter_factory(global_conf, **local_conf)
        return factory(app)

    def start_response(self, status, headers):
        self.got_statuses.append(status)

    def test_load_app(self):
        try:
            self.get_app(FakeApp(), DEFAULT_CONFIG)
        except Exception:
            self.fail('Application loading got an error')

    def test_GET_without_storlets(self):
        def basic_get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(FakeApp(), DEFAULT_CONFIG)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])

        for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
            path = join('/', 'v1', target)
            basic_get(path)


if __name__ == '__main__':
    unittest.main()

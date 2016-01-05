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

import copy
import mock
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
        'storlet_gateway.storlet_stub_gateway:StorletGatewayStub',
    'storlet_gateway_conf': '/etc/swift/storlet_stub_gateway.conf',
    'execution_server': 'proxy'}


class TestStorletsHandler(unittest.TestCase):
    def setUp(self):
        self.got_statuses = []
        self.conf = copy.copy(DEFAULT_CONFIG)

    def tearDown(self):
        pass

    def get_app(self, app, global_conf, **local_conf):
        factory = storlet_handler.filter_factory(global_conf, **local_conf)
        return factory(app)

    def start_response(self, status, headers):
        self.got_statuses.append(status)

    # TODO(takashi): We don't have to run this test for base class
    def test_load_app(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, body='FAKE APP')(
                    env, start_response)

        try:
            self.get_app(FakeApp(), self.conf)
        except Exception:
            self.fail('Application loading got an error')


class TestStorletHandlerProxy(TestStorletsHandler):
    def setUp(self):
        super(TestStorletHandlerProxy, self).setUp()
        self.conf['execution_server'] = 'proxy'

    def test_GET_without_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, body='FAKE APP')(
                    env, start_response)

        def basic_get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])

        for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
            path = join('/', 'v1', target)
            basic_get(path)

    def test_GET_with_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                if env['PATH_INFO'] == '/v1/AUTH_a/storlets/Storlet-1.0.jar':
                    return Response(status='200 OK')(env, start_response)
                elif env['PATH_INFO'] == '/v1/AUTH_a/c/o':
                    return Response(request=Request(env), body='FAKE RESULT')(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE RESULT'])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/o')

    def test_GET_with_storlets_disabled_account(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                if env['PATH_INFO'] == '/v1/AUTH_a/storlets/Storlet-1.0.jar':
                    return Response(status='200 OK')(env, start_response)
                elif env['PATH_INFO'] == '/v1/AUTH_a/c/o':
                    return Response(request=Request(env), body='FAKE RESULT')(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('400 Bad Request', self.got_statuses[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/o')

    def test_GET_with_storlets_object_404(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                if env['PATH_INFO'] == '/v1/AUTH_a/storlets/Storlet-1.0.jar':
                    return Response(status='200 OK')(env, start_response)
                elif env['PATH_INFO'] == '/v1/AUTH_a/c/o':
                    return Response(status='404 Not Found')(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('404 Not Found', self.got_statuses[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/o')


class TestStorletHandlerObject(TestStorletsHandler):
    def setUp(self):
        super(TestStorletHandlerObject, self).setUp()
        self.conf['execution_server'] = 'object'

    def test_GET_without_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, body='FAKE APP')(
                    env, start_response)

        def basic_get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])

        basic_get('/sda1/p/AUTH_a/c/o')

    def test_GET_with_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, body='FAKE APP')(
                    env, start_response)

        def get(path):
            print(self.conf['execution_server'])
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['DUMMY_CONTENT'])

        get('/sda1/p/AUTH_a/c/o')

if __name__ == '__main__':
    unittest.main()

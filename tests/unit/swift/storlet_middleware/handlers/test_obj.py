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

import mock
import unittest

from swift.common.swob import Request, HTTPOk, HTTPCreated
from storlet_middleware.handlers import StorletObjectHandler

from tests.unit.swift.storlet_middleware.handlers import \
    BaseTestStorletMiddleware


class TestStorletMiddlewareObject(BaseTestStorletMiddleware):
    def setUp(self):
        super(TestStorletMiddlewareObject, self).setUp()
        self.conf['execution_server'] = 'object'

    def test_call_unsupported_method(self):
        def call(method):
            path = '/sda1/p/AUTH_a/c/o'
            headers = {'X-Backend-Storlet-Policy-Index': '0',
                       'X-Run-Storlet': 'Storlet-1.0.jar'}
            req = Request.blank(path, environ={'REQUEST_METHOD': method},
                                headers=headers)
            app = self.get_app(lambda env, start: None, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('405 Method Not Allowed', self.got_statuses[-1])

        for method in ('POST', 'PUT', 'DELETE'):
            call(method)

    def test_PUT_objet_into_storlets_container(self):
        target = '/sda1/p/AUTH_a/storlet/storlet-1.0.jar'
        self.app.register('PUT', target, HTTPCreated)

        sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                    'X-Object-Meta-Storlet-Interface-Version': '1.0',
                    'X-Object-Meta-Storlet-Dependency': 'dependency',
                    'X-Object-Meta-Storlet-Main':
                        'org.openstack.storlet.Storlet'}
        req = Request.blank(target, environ={'REQUEST_METHOD': 'PUT'},
                            headers=sheaders)
        app = self.get_app(self.app, self.conf)
        app(req.environ, self.start_response)
        self.assertEqual('201 Created', self.got_statuses[-1])

    def test_GET_without_storlets(self):
        def basic_get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0'})
            self.app.register('GET', path, HTTPOk, body='FAKE APP')
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])
            self.app.reset_all()

        for target in ('/sda1/p/AUTH_a', '/sda1/p/AUTH_a/c',
                       '/sda1/p/AUTH_a/c/o'):
            basic_get(target)

    def test_GET_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        app = self.get_app(self.app, self.conf)
        resp = app(req.environ, self.start_response)
        self.assertEqual('200 OK', self.got_statuses[-1])
        self.assertEqual(resp.read(), 'FAKE APP')

    def test_GET_with_storlets_and_http_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'Range': 'bytes=10-20'})
        app = self.get_app(self.app, self.conf)
        app(req.environ, self.start_response)
        self.assertEqual('416 Requested Range Not Satisfiable',
                         self.got_statuses[-1])

    def test_GET_with_storlets_and_storlet_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Range': 'bytes=1-6',
                     'Range': 'bytes=1-6'})
        app = self.get_app(self.app, self.conf)
        resp = app(req.environ, self.start_response)
        self.assertEqual('206 Partial Content',
                         self.got_statuses[-1])
        self.assertEqual(resp, ['AKE AP'])

    def test_GET_slo_manifest_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk,
                          headers={'X-Static-Large-Object': 'True'},
                          body='FAKE MANIFEST')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        app = self.get_app(self.app, self.conf)
        resp = app(req.environ, self.start_response)
        self.assertEqual('200 OK', self.got_statuses[-1])
        self.assertEqual(resp, ['FAKE MANIFEST'])

    def test_GET_slo_segment_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk,
                          headers={'X-Static-Large-Object': 'True'},
                          body='FAKE SEGMENT')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'multipart-manifest': 'get',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        app = self.get_app(self.app, self.conf)
        resp = app(req.environ, self.start_response)
        self.assertEqual('200 OK', self.got_statuses[-1])
        self.assertEqual(resp, ['FAKE SEGMENT'])

    def test_storlets_with_invalid_method(self):
        target = '/sda1/p/AUTH_a/c/o'

        req = Request.blank(
            target, environ={'REQUEST_METHOD': '_parse_vaco'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        app = self.get_app(self.app, self.conf)
        app(req.environ, self.start_response)
        self.assertEqual('405 Method Not Allowed', self.got_statuses[-1])


class TestStorletObjectHandler(unittest.TestCase):
    def setUp(self):
        self.handler_class = StorletObjectHandler

    def test_init_handler(self):
        req = Request.blank(
            '/dev/part/acc/cont/obj', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        handler = self.handler_class(
            req, mock.MagicMock(), mock.MagicMock(), mock.MagicMock())
        # FIXME: stil hold api version 0 at ObjectHandler but will be
        #        deprecated if it's never used.
        self.assertEqual('0', handler.api_version)
        self.assertEqual('acc', handler.account)
        self.assertEqual('cont', handler.container)
        self.assertEqual('obj', handler.obj)

        req = Request.blank(
            '/dev/part/acc2/cont2/obj2', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        handler.request = req
        self.assertEqual('/dev/part/acc2/cont2/obj2', handler.request.path)
        self.assertEqual('0', handler.api_version)
        self.assertEqual('acc2', handler.account)
        self.assertEqual('cont2', handler.container)
        self.assertEqual('obj2', handler.obj)

        # no direct assignment allowed
        with self.assertRaises(AttributeError):
            handler.api_version = '1'

        with self.assertRaises(AttributeError):
            handler.account = 'acc'

        with self.assertRaises(AttributeError):
            handler.container = 'cont'

        with self.assertRaises(AttributeError):
            handler.obj = 'obj'


if __name__ == '__main__':
    unittest.main()
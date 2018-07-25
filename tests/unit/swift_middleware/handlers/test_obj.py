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
from storlets.swift_middleware.handlers import StorletObjectHandler

from tests.unit.swift_middleware.handlers import \
    BaseTestStorletMiddleware, create_handler_config


class TestStorletMiddlewareObject(BaseTestStorletMiddleware):
    def setUp(self):
        super(TestStorletMiddlewareObject, self).setUp(exec_server='object')

    def test_load_app(self):
        try:
            self.get_app(self.base_app, self.conf)
        except Exception:
            self.fail('Application loading got an error')

    def test_call_unsupported_method(self):
        def call(method):
            path = '/sda1/p/AUTH_a/c/o'
            headers = {'X-Backend-Storlet-Policy-Index': '0',
                       'X-Run-Storlet': 'Storlet-1.0.jar'}
            req = Request.blank(path, environ={'REQUEST_METHOD': method},
                                headers=headers)
            resp = self.get_response(req)
            self.assertEqual('405 Method Not Allowed', resp.status)

        for method in ('POST', 'PUT', 'DELETE'):
            call(method)

    def test_PUT_objet_into_storlets_container(self):
        target = '/sda1/p/AUTH_a/storlet/storlet-1.0.jar'
        self.base_app.register('PUT', target, HTTPCreated)

        sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                    'X-Object-Meta-Storlet-Interface-Version': '1.0',
                    'X-Object-Meta-Storlet-Dependency': 'dependency',
                    'X-Object-Meta-Storlet-Main':
                        'org.openstack.storlet.Storlet'}
        req = Request.blank(target, environ={'REQUEST_METHOD': 'PUT'},
                            headers=sheaders)
        resp = self.get_response(req)
        self.assertEqual('201 Created', resp.status)

    def test_GET_without_storlets(self):
        def basic_get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0'})
            self.base_app.register('GET', path, HTTPOk, body=b'FAKE APP')
            resp = self.get_response(req)
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)
            self.base_app.reset_all()

        for target in ('/sda1/p/AUTH_a', '/sda1/p/AUTH_a/c',
                       '/sda1/p/AUTH_a/c/o'):
            basic_get(target)

    def test_GET_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        resp = self.get_response(req)
        self.assertEqual('200 OK', resp.status)
        self.assertEqual(b'FAKE APP', resp.body)

    def test_GET_with_storlets_and_http_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'Range': 'bytes=10-20'})
        resp = self.get_response(req)
        self.assertEqual('416 Requested Range Not Satisfiable',
                         resp.status)

    def test_GET_with_storlets_and_storlet_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Range': 'bytes=1-6',
                     'Range': 'bytes=1-6'})
        resp = self.get_response(req)
        self.assertEqual('200 OK', resp.status)
        self.assertEqual(b'AKE AP', resp.body)
        self.assertEqual('bytes 1-6/8',
                         resp.headers.get('Storlet-Input-Range'))

    def test_GET_with_storlets_and_storlet_proxy_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Range': 'bytes=1-6',
                     'Range': 'bytes=1-6',
                     'X-Storlet-Run-On-Proxy': ''})
        resp = self.get_response(req)
        self.assertEqual('206 Partial Content', resp.status)
        self.assertEqual(b'AKE AP', resp.body)
        self.assertEqual('bytes 1-6/8',
                         resp.headers.get('Content-Range'))

    def test_GET_slo_manifest_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk,
                               headers={'X-Static-Large-Object': 'True'},
                               body=b'FAKE MANIFEST')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        resp = self.get_response(req)
        self.assertEqual('200 OK', resp.status)
        self.assertEqual(b'FAKE MANIFEST', resp.body)

    def test_GET_slo_segment_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk,
                               headers={'X-Static-Large-Object': 'True'},
                               body=b'FAKE SEGMENT')

        req = Request.blank(
            target, environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'multipart-manifest': 'get',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        resp = self.get_response(req)
        self.assertEqual('200 OK', resp.status)
        self.assertEqual(b'FAKE SEGMENT', resp.body)

    def test_storlets_with_invalid_method(self):
        target = '/sda1/p/AUTH_a/c/o'

        req = Request.blank(
            target, environ={'REQUEST_METHOD': '_parse_vaco'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        resp = self.get_response(req)
        self.assertEqual('405 Method Not Allowed', resp.status)


class TestStorletObjectHandler(unittest.TestCase):
    def setUp(self):
        self.handler_class = StorletObjectHandler
        self.conf = create_handler_config('object')
        self.gateway_conf = {}

    def test_init_handler(self):
        req = Request.blank(
            '/dev/part/acc/cont/obj', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storage-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        handler = self.handler_class(
            req, self.conf, self.gateway_conf, mock.MagicMock(),
            mock.MagicMock())
        # FIXME: stil hold api version 0 at ObjectHandler but will be
        #        deprecated if it's never used.
        self.assertEqual('0', handler.api_version)
        self.assertEqual('acc', handler.account)
        self.assertEqual('cont', handler.container)
        self.assertEqual('obj', handler.obj)

        req = Request.blank(
            '/dev/part/acc2/cont2/obj2', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storage-Policy-Index': '0',
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

    def test_get_storlet_invocation_options(self):
        req = Request.blank(
            '/dev/part/acc/cont/obj',
            environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storage-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Foo': 'baa'})
        handler = self.handler_class(
            req, self.conf, self.gateway_conf, mock.MagicMock(),
            mock.MagicMock())

        options = handler._get_storlet_invocation_options(req)
        self.assertEqual('baa', options['storlet_foo'])
        self.assertFalse(options['generate_log'])

        req = Request.blank(
            '/dev/part/acc/cont/obj',
            environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storage-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Foo': 'baa',
                     'X-Storlet-Generate-Log': 'True'})
        handler = self.handler_class(
            req, self.conf, self.gateway_conf, mock.MagicMock(),
            mock.MagicMock())

        options = handler._get_storlet_invocation_options(req)
        self.assertEqual('baa', options['storlet_foo'])
        self.assertTrue(options['generate_log'])

        req = Request.blank(
            '/dev/part/acc/cont/obj',
            environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storage-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Foo': 'baa',
                     'X-Storlet-Range': 'bytes=1-6',
                     'Range': 'bytes=1-6'})
        handler = self.handler_class(
            req, self.conf, self.gateway_conf, mock.MagicMock(),
            mock.MagicMock())

        options = handler._get_storlet_invocation_options(req)
        self.assertEqual('baa', options['storlet_foo'])
        self.assertFalse(options['generate_log'])
        self.assertNotIn('storlet_range', options)
        self.assertEqual(1, options['range_start'])
        self.assertEqual(7, options['range_end'])


if __name__ == '__main__':
    unittest.main()

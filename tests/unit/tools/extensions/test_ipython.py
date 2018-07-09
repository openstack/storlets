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

from IPython.core.error import UsageError
from six.moves import StringIO
from storlets.tools.extensions.ipython import StorletMagics
import unittest
import mock
import os
import itertools

import six
if six.PY3:
    from io import FileIO as file


class FakeConnection(object):
    def __init__(self, fake_status=200, fake_headers=None, fake_iter=None):
        self._fake_status = fake_status
        self._fake_headers = fake_headers or {}
        self._fake_iter = fake_iter or iter([])

    def _return_fake_response(self, **kwargs):
        if 'response_dict' in kwargs:
            kwargs['response_dict']['status'] = self._fake_status
            kwargs['response_dict']['headers'] = self._fake_headers
            kwargs['response_dict']['content_iter'] = self._fake_iter

        if 'resp_chunk_size' in kwargs:
            resp_body = self._fake_iter
        else:
            resp_body = ''.join([chunk for chunk in self._fake_iter])

        return (self._fake_headers, resp_body)

    # Those 3 methods are just for entry point difference from the caller
    # but all methods returns same response format with updateing response_dict
    def get_object(self, *args, **kwargs):
        return self._return_fake_response(**kwargs)

    def copy_object(self, *args, **kwargs):
        return self._return_fake_response(**kwargs)

    def put_object(self, *args, **kwargs):
        return self._return_fake_response(**kwargs)


class MockShell(object):
    def __init__(self):
        self.user_ns = {}

    def register(self, var_name, value):
        self.user_ns[var_name] = value


class BaseTestIpythonExtension(object):
    def setUp(self):
        self.magics = StorletMagics()
        # set auth info for keystone
        self.os_original_env = os.environ.copy()
        self._set_auth_environ()
        self.magics.shell = MockShell()

    def tearDown(self):
        os.environ = self.os_original_env.copy()

    def _set_auth_environ(self):
        # helper method to set auth information for keystone v3 (default)
        os.environ['OS_AUTH_VERSION'] = '3'
        os.environ['OS_AUTH_URL'] = 'http://127.0.0.1/identity/v3'
        os.environ['OS_USERNAME'] = 'tester'
        os.environ['OS_PASSWORD'] = 'testing'
        os.environ['OS_USER_DOMAIN_NAME'] = 'default'
        os.environ['OS_PROJECT_DOMAIN_NAME'] = 'default'
        os.environ['OS_PROJECT_NAME'] = 'test'

    @mock.patch('storlets.tools.extensions.ipython.Connection')
    def _call_cell(self, func, line, cell, fake_conn):
        fake_conn.return_value = self.fake_connection
        # cell magic
        func(line, cell)

    @mock.patch('storlets.tools.extensions.ipython.Connection')
    def _call_line(self, func, line, fake_conn):
        fake_conn.return_value = self.fake_connection
        # line magic
        func(line)


class TestStorletMagicStorletApp(BaseTestIpythonExtension, unittest.TestCase):
    def setUp(self):
        super(TestStorletMagicStorletApp, self).setUp()
        self.fake_connection = FakeConnection()

    def _call_storletapp(self, line, cell):
        self._call_cell(self.magics.storletapp, line, cell)

    def test_storlet_magics(self):
        line = 'test.TestStorlet'
        cell = ''
        self._call_storletapp(line, cell)

    def test_storlet_magics_usage_error(self):
        # no line result in UsageError (from ipython default behavior)
        line = ''
        cell = ''
        self.assertRaises(
            UsageError, self._call_storletapp, line, cell)

    def test_storlet_magics_with_invoke(self):
        line = 'test.TestStorlet --with-invoke --input path:/foo/bar'
        cell = ''
        self._call_storletapp(line, cell)

    def test_storlet_magics_with_invoke_no_input_fail(self):
        line = 'test.TestStorlet --with-invoke'
        cell = ''
        with self.assertRaises(UsageError) as cm:
            self._call_storletapp(line, cell)
        self.assertEqual(
            '--with-invoke option requires --input to run the app',
            cm.exception.args[0])

    def test_storlet_magics_invalid_input_fail(self):
        invalid_input_patterns = (
            'invalid',  # no "path:" prefix
            'path://',  # no container object in the slash
            'path:/container',  # only container
            'path:container',  # only container w/o slash prefix
        )

        for invalid_input in invalid_input_patterns:
            with self.assertRaises(UsageError) as cm:
                self.magics._parse_input_path(invalid_input)
            self.assertEqual(
                'swift object path must have the format: '
                '"path:/<container>/<object>"',
                cm.exception.args[0])

    def test_storlet_magics_stdout(self):
        line = 'test.TestStorlet --with-invoke --input path:/foo/bar' \
               '--print-result'
        cell = ''
        fake_stdout = StringIO()
        with mock.patch('sys.stdout', fake_stdout):
            self._call_storletapp(line, cell)
        stdout_string = fake_stdout.getvalue()
        expected_outputs = (
            'Upload storlets succeeded',
            'Example command `swift download <container> <object> '
            '-H X-Run-Storlet:',
            'Invocation Complete',
        )

        for expected in expected_outputs:
            self.assertIn(expected, stdout_string)

    def test_storlet_auth_v3_no_enough_auth_info(self):
        line = 'test.TestStorlet'
        cell = ''

        # OS_AUTH_URL, OS_USERNAME, OS_PASSWORD, OS_PROJECT_NAME are required
        required = ('OS_AUTH_URL', 'OS_USERNAME',
                    'OS_PASSWORD', 'OS_PROJECT_NAME')

        for combi_length in range(1, len(required) + 1):
            for combination in itertools.combinations(required, combi_length):
                # set full environ for auth
                self._set_auth_environ()
                # and delete specific required keys
                for key in combination:
                    del os.environ[key]

                with self.assertRaises(UsageError) as e:
                    self._call_storletapp(line, cell)

                self.assertEqual(
                    "You need to set OS_AUTH_URL, OS_USERNAME, OS_PASSWORD "
                    "and OS_PROJECT_NAME for Swift authentication",
                    e.exception.args[0])

    def test_storlet_auth_v2_not_supported(self):
        line = 'test.TestStorlet'
        cell = ''
        os.environ['OS_AUTH_VERSION'] = '2'
        with self.assertRaises(NotImplementedError) as e:
            self._call_storletapp(line, cell)
        self.assertEqual(
            'keystone v2 is not supported',
            e.exception.args[0])

    def test_storlet_auth_v1_no_enough_auth_info(self):
        # NOTE: Now, storlets should work on keystone v3 so that this test
        # may be deprecated in the future if we don't have to support pure
        # swift upstream v1 auth (e.g. tempauth).
        line = 'test.TestStorlet'
        cell = ''

        # ST_AUTH, ST_USER, ST_KEY are required
        required = ('ST_AUTH', 'ST_USER', 'ST_KEY')

        # v1 doesn't require OS_AUTH_VERSION
        del os.environ['OS_AUTH_VERSION']
        try:
            del os.environ['OS_IDENTITY_API_VERSION']
        except Exception:
            pass

        def _set_v1_auth():
            os.environ['ST_AUTH'] = 'http://localhost/v1/auth'
            os.environ['ST_USER'] = 'test:tester'
            os.environ['ST_KEY'] = 'testing'

        for combi_length in range(1, len(required) + 1):
            for combination in itertools.combinations(required, combi_length):
                # set full environ for auth
                _set_v1_auth()
                # and delete specific required keys
                for key in combination:
                    del os.environ[key]

                with self.assertRaises(UsageError) as e:
                    self._call_storletapp(line, cell)

                self.assertEqual(
                    "You need to set ST_AUTH, ST_USER, ST_KEY "
                    "for Swift authentication",
                    e.exception.args[0])


class TestStorletMagicGet(BaseTestIpythonExtension, unittest.TestCase):
    def setUp(self):
        super(TestStorletMagicGet, self).setUp()
        self.fake_connection = FakeConnection()

    def _call_get(self, line):
        self._call_line(self.magics.get, line)

    def test_get_invalid_args(self):
        scenarios = [
            {
                'line': '--input path:/c/o --storlet a.b',
                'exception': UsageError,
                'msg': '-o option is mandatory for the invocation'
            }, {
                'line': '--input path:/c/o -o a1234',
                'exception': UsageError,
                'msg': '--storlet option is mandatory for the invocation'
            }, {
                'line': '--storlet a.b -o a1234',
                'exception': UsageError,
                'msg': '--input option is mandatory for the invocation'
            }, {
                'line': '--input path/c/o --storlet a.b -o a1234',
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': '--input path:/c/ --storlet a.b -o a1234',
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': '--input path:/c --storlet a.b -o a1234',
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': '--input path:/c/o --storlet a.b -o 1234',
                'exception': UsageError,
                'msg': ('The output variable name must be a valid prefix '
                        'of a python variable, that is, start with a '
                        'letter')
            }]

        for scenario in scenarios:
            with self.assertRaises(UsageError) as e:
                self._call_get(scenario['line'])
            self.assertEqual(scenario['msg'], e.exception.args[0])

    def _test_get(self, line, outvar_name):
        self._call_get(line)
        self.assertTrue(outvar_name in self.magics.shell.user_ns)
        resp = self.magics.shell.user_ns[outvar_name]
        self.assertEqual({}, resp.headers)
        self.assertEqual(200, resp.status)
        self.assertEqual('', ''.join([chunk for chunk in iter(resp)]))
        self.assertEqual('', resp.content)

    def test_get(self):
        outvar_name = 'a1234'
        line = '--input path:/c/o --storlet a.b -o %s' % outvar_name
        self._test_get(line, outvar_name)

    def test_get_with_input(self):
        params_name = 'params'
        outvar_name = 'a1234'
        line = '--input path:/c/o --storlet a.b -o %s -i %s' % (outvar_name,
                                                                params_name)
        # register the variable to user_ns
        self.magics.shell.register(params_name, {'a': 'b'})
        self._test_get(line, outvar_name)

    def test_get_with_input_error(self):
        params_name = 'params'
        outvar_name = 'a1234'
        line = '--input path:/c/o --storlet a.b -o %s -i %s' % (outvar_name,
                                                                params_name)
        with self.assertRaises(KeyError):
            self._test_get(line, outvar_name)


class TestStorletMagicCopy(BaseTestIpythonExtension, unittest.TestCase):
    def setUp(self):
        super(TestStorletMagicCopy, self).setUp()
        self.fake_connection = FakeConnection()

    def _call_copy(self, line):
        self._call_line(self.magics.copy, line)

    def test_copy_invalid_args(self):
        scenarios = [
            {
                'line': '--input path:/c/o --storlet a.b --output path:/c/o',
                'exception': UsageError,
                'msg': '-o option is mandatory for the invocation'
            }, {
                'line': ('--input path:/c/o --storlet a.b -o 1234 '
                         '--output path:/c/o'),
                'exception': UsageError,
                'msg': ('The output variable name must be a valid prefix '
                        'of a python variable, that is, start with a '
                        'letter')
            }, {
                'line': '--input path:/c/o -o a1234 --output path:/c/o',
                'exception': UsageError,
                'msg': '--storlet option is mandatory for the invocation'
            }, {
                'line': '--storlet a.b -o a1234 --output path:/c/o',
                'exception': UsageError,
                'msg': '--input option is mandatory for the invocation'
            }, {
                'line': ('--input path/c/o --storlet a.b -o a1234 '
                         '--output path:/c/o'),
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': ('--input path:/c/ --storlet a.b -o a1234 '
                         '--output path:/c/o'),
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': ('--input path:/c --storlet a.b -o a1234 '
                         '--output path:/c/o'),
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': '--input path:/c --storlet a.b -o a1234 ',
                'exception': UsageError,
                'msg': ('--output option is mandatory for the invocation')
            }, {
                'line': ('--input path:/c --storlet a.b -o a1234 '
                         '--output path/c/o'),
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }]

        for scenario in scenarios:
            with self.assertRaises(UsageError) as e:
                self._call_copy(scenario['line'])
            self.assertEqual(scenario['msg'], e.exception.args[0])

    def _test_copy(self, line, outvar_name):
        self._call_copy(line)
        self.assertTrue(outvar_name in self.magics.shell.user_ns)
        resp = self.magics.shell.user_ns[outvar_name]
        self.assertEqual({}, resp.headers)
        self.assertEqual(200, resp.status)
        # sanity, no body
        self.assertEqual('', resp.content)

    def test_copy(self):
        outvar_name = 'a1234'
        line = ('--input path:/c/o --output path:/c/o '
                '--storlet a.b -o %s' % outvar_name)
        self._test_copy(line, outvar_name)

    def test_copy_stdout_with_input(self):
        params_name = 'params'
        outvar_name = 'a1234'
        line = ('--input path:/c/o --output path:/c/o '
                '--storlet a.b -o %s -i %s' % (outvar_name, params_name))
        self.magics.shell.register(params_name, {'a': 'b'})
        self._test_copy(line, outvar_name)

    def test_copy_stdout_with_input_error(self):
        params_name = 'params'
        outvar_name = 'a1234'
        line = ('--input path:/c/o --output path:/c/o '
                '--storlet a.b -o %s -i %s' % (outvar_name, params_name))
        with self.assertRaises(KeyError):
            self._test_copy(line, outvar_name)


class TestStorletMagicPut(BaseTestIpythonExtension, unittest.TestCase):
    def setUp(self):
        super(TestStorletMagicPut, self).setUp()
        self.fake_connection = FakeConnection(201)

    def _call_put(self, line):
        self._call_line(self.magics.put, line)

    def test_put_invalid_args(self):
        scenarios = [
            {
                'line': '--input /c/o --storlet a.b --output path:/c/o',
                'exception': UsageError,
                'msg': '-o option is mandatory for the invocation'
            }, {
                'line': ('--input /c/o --storlet a.b -o 1234 '
                         '--output path:/c/o'),
                'exception': UsageError,
                'msg': ('The output variable name must be a valid prefix '
                        'of a python variable, that is, start with a '
                        'letter')
            }, {
                'line': '--input /c/o -o a1234 --output path:/c/o',
                'exception': UsageError,
                'msg': '--storlet option is mandatory for the invocation'
            }, {
                'line': '--storlet a.b -o a1234 --output path:/c/o',
                'exception': UsageError,
                'msg': '--input option is mandatory for the invocation'
            }, {
                'line': ('--input /c/o --storlet a.b -o a1234 '
                         '--output path/c/o'),
                'exception': UsageError,
                'msg': ('swift object path must have the format: '
                        '"path:/<container>/<object>"')
            }, {
                'line': ('--input path:c/ --storlet a.b -o a1234 '
                         '--output path:/c/o'),
                'exception': UsageError,
                'msg': ('--input argument must be a full path')
            }]

        for scenario in scenarios:
            with self.assertRaises(UsageError) as e:
                self._call_put(scenario['line'])
            self.assertEqual(scenario['msg'], e.exception.args[0])

    def _test_put(self, line, outvar_name):
        open_name = '%s.open' % 'storlets.tools.extensions.ipython'
        with mock.patch(open_name, create=True) as mock_open:
            mock_open.return_value = mock.MagicMock(spec=file)
            self._call_put(line)
        self.assertTrue(outvar_name in self.magics.shell.user_ns)
        resp = self.magics.shell.user_ns[outvar_name]
        self.assertEqual({}, resp.headers)
        self.assertEqual(201, resp.status)
        # sanity, no body
        self.assertEqual('', resp.content)

    def test_put(self):
        outvar_name = 'a1234'
        line = ('--input /c/o --storlet a.b '
                '--output path:a/b -o %s' % outvar_name)
        self._test_put(line, outvar_name)

    def test_put_stdout_with_input(self):
        params_name = 'params'
        outvar_name = 'a1234'
        line = ('--input /c/o --storlet a.b -o %s -i %s '
                '--output path:a/b' % (outvar_name, params_name))
        self.magics.shell.register(params_name, {'a': 'b'})
        self._test_put(line, outvar_name)

    def test_put_stdout_with_input_error(self):
        params_name = 'params'
        outvar_name = 'a1234'
        line = ('--input /c/o --storlet a.b -o %s -i %s '
                '--output path:a/b' % (outvar_name, params_name))
        with self.assertRaises(KeyError):
            self._test_put(line, outvar_name)


if __name__ == '__main__':
    unittest.main()

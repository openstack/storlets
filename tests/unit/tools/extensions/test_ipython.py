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
from cStringIO import StringIO
from storlets.tools.extensions.ipython import StorletMagics
import unittest
import mock
import os
import itertools


class FakeConnection(mock.MagicMock):
    def get_object(self, *args, **kwargs):
        return (mock.MagicMock(), mock.MagicMock())


class TestStorletMagics(unittest.TestCase):
    def setUp(self):
        self.fake_connection = FakeConnection()
        self.magics = StorletMagics()
        # set auth info for keystone
        self.os_original_env = os.environ.copy()
        self._set_auth_environ()

    def tearDown(self):
        os.environ = self.os_original_env.copy()

    def _set_auth_environ(self):
        # helper method to set auth information for keystone v3 (default)
        os.environ['OS_AUTH_VERSION'] = '3'
        os.environ['OS_AUTH_URL'] = 'http://127.0.0.1:5000/v3'
        os.environ['OS_USERNAME'] = 'tester'
        os.environ['OS_PASSWORD'] = 'testing'
        os.environ['OS_USER_DOMAIN_NAME'] = 'default'
        os.environ['OS_PROJECT_DOMAIN_NAME'] = 'default'
        os.environ['OS_PROJECT_NAME'] = 'test'

    def _call_storletapp(self, line, cell):
        # wrap up the get_swift_connection always return mock connection
        with mock.patch(
                'storlets.tools.extensions.ipython.Connection') as fake_conn:
            fake_conn.return_value = self.fake_connection
            self.magics.storletapp(line, cell)

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
            cm.exception.message)

    def test_storlet_magics_with_invoke_invalid_input_fail(self):
        cell = ''
        invalid_input_patterns = (
            'invalid',  # no "path:" prefix
            'path://',  # no container object in the slash
            'path:/container',  # only container
            'path:container',  # only container w/o slash prefix
        )

        for invalid_input in invalid_input_patterns:
            line = 'test.TestStorlet --with-invoke --input %s' % invalid_input
            with self.assertRaises(UsageError) as cm:
                self._call_storletapp(line, cell)
            self.assertEqual(
                '--input option for --with-invoke must be path format '
                '"path:/<container>/<object>"',
                cm.exception.message)

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
                    e.exception.message)

    def test_storlet_auth_v2_not_supported(self):
        line = 'test.TestStorlet'
        cell = ''
        os.environ['OS_AUTH_VERSION'] = '2'
        with self.assertRaises(NotImplementedError) as e:
            self._call_storletapp(line, cell)
        self.assertEqual(
            'keystone v2 is not supported',
            e.exception.message)

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
                    e.exception.message)


if __name__ == '__main__':
    unittest.main()

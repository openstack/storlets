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

from tests.unit.swift import FakeLogger
import mock
import os
import storlet_gateway.storlet_runtime
import unittest


class TestRuntimePaths(unittest.TestCase):

    def setUp(self):
        self.account = 'AUTH_0123456789abcdefghijklmnopqrstuv'
        self.scope = '0123456789abc'
        self._initialize()

    def _initialize(self):
        # TODO(takashi): take these values from config file
        base_dir = '/home/docker_device'
        self.conf = {
            'script_dir': os.path.join(base_dir, 'scripts'),
            'pipes_dir': os.path.join(base_dir, 'pipes', 'scopes'),
            'storlets_dir': os.path.join(base_dir, 'storlets', 'scopes'),
            'log_dir': os.path.join(base_dir, 'logs', 'scopes'),
            'cache_dir': os.path.join(base_dir, 'cache', 'scopes'),
            'reseller_prefix': 'AUTH',
            'storlet_container': 'storlet',
            'storlet_dependency': 'dependency'}
        self.storlet_id = 'org.openstack.storlet.mystorlet'
        self.paths = storlet_gateway.storlet_runtime.RunTimePaths(
            self.account, self.conf)

    def tearDown(self):
        pass

    def test_host_pipe_prefix(self):
        self.assertEqual(
            self.paths.host_pipe_prefix(),
            os.path.join(self.conf['pipes_dir'], self.scope))

    def test_create_host_pipe_prefix(self):
        pipedir = self.paths.host_pipe_prefix()

        # When the directory exists
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.makedirs') as m:
                with mock.patch('os.chmod') as c:
                    self.paths.create_host_pipe_prefix()
                    self.assertEqual(m.call_count, 0)
                    cargs, ckwargs = c.call_args
                    # Make sure about the target directory
                    self.assertEqual(
                        cargs[0], pipedir)

        # When the directory does not exist
        with mock.patch('os.path.exists', return_value=False):
            with mock.patch('os.makedirs') as m:
                with mock.patch('os.chmod') as c:
                    self.paths.create_host_pipe_prefix(),
                    self.assertEqual(m.call_count, 1)
                    # Make sure about the target directory
                    margs, mkwargs = m.call_args
                    self.assertEqual(
                        margs[0], pipedir)
                    cargs, ckwargs = c.call_args
                    self.assertEqual(
                        cargs[0], pipedir)

    def test_host_factory_pipe(self):
        self.assertEqual(
            self.paths.host_factory_pipe(),
            os.path.join(self.conf['pipes_dir'], self.scope,
                         'factory_pipe'))

    def test_host_storlet_pipe(self):
        self.assertEqual(
            self.paths.host_storlet_pipe(self.storlet_id),
            os.path.join(self.conf['pipes_dir'], self.scope,
                         self.storlet_id))

    def test_sbox_storlet_pipe(self):
        self.assertEqual(
            self.paths.sbox_storlet_pipe(self.storlet_id),
            os.path.join('/mnt/channels', self.storlet_id))

    def test_sbox_storlet_exec(self):
        self.assertEqual(
            self.paths.sbox_storlet_exec(self.storlet_id),
            os.path.join('/home/swift', self.storlet_id))

    def test_host_storlet_prefix(self):
        self.assertEqual(
            self.paths.host_storlet_prefix(),
            os.path.join(self.conf['storlets_dir'], self.scope))

    def test_host_storlet(self):
        self.assertEqual(
            self.paths.host_storlet(self.storlet_id),
            os.path.join(self.conf['storlets_dir'], self.scope,
                         self.storlet_id))

    def test_slog_path(self):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.makedirs') as m:
                self.assertEqual(
                    self.paths.slog_path(self.storlet_id),
                    os.path.join(self.conf['log_dir'], self.scope,
                                 self.storlet_id))
                self.assertEqual(m.call_count, 0)

        with mock.patch('os.path.exists', return_value=False):
            with mock.patch('os.makedirs') as m:
                self.assertEqual(
                    self.paths.slog_path(self.storlet_id),
                    os.path.join(self.conf['log_dir'], self.scope,
                                 self.storlet_id))
                self.assertEqual(m.call_count, 1)

    def test_get_host_storlet_cache_dir(self):
        self.assertEqual(
            self.paths.get_host_storlet_cache_dir(),
            os.path.join(self.conf['cache_dir'], self.scope,
                         self.conf['storlet_container']))

    def test_get_host_dependency_cache_dir(self):
        self.assertEqual(
            self.paths.get_host_dependency_cache_dir(),
            os.path.join(self.conf['cache_dir'], self.scope,
                         self.conf['storlet_dependency']))


class TestRuntimePathsTempauth(TestRuntimePaths):

    def setUp(self):
        self.account = 'AUTH_test'
        self.scope = 'test'
        self._initialize()


class TestRunTimeSandbox(unittest.TestCase):

    def setUp(self):
        self.logger = FakeLogger()
        # TODO(takashi): take these values from config file
        self.conf = {'restart_linux_container_timeout': 3,
                     'docker_repo': 'localhost:5001'}
        self.account = 'AUTH_0123456789abcdefghijklmnopqrstuv'
        self.run_time_sbox = storlet_gateway.storlet_runtime.RunTimeSandbox(
            self.account, self.conf, self.logger)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()

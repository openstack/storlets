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
import os
import unittest
import tempfile
from contextlib import contextmanager
from six import StringIO

from storlet_middleware.storlet_common import StorletRuntimeException
from storlet_gateway.storlet_docker_gateway import DockerStorletRequest
import storlet_gateway.storlet_runtime
from swift.common.swob import Request
from tests.unit.swift import FakeLogger


@contextmanager
def _mock_sbus(send_status=0):
    with mock.patch('storlet_gateway.storlet_runtime.'
                    'SBusDatagram.create_service_datagram'), \
        mock.patch('storlet_gateway.storlet_runtime.'
                   'SBus.send') as fake_send:
        fake_send.return_value = send_status
        yield


@contextmanager
def _mock_os_pipe(bufs):
    class FakeFd(object):
        def __init__(self, rbuf=''):
            self.rbuf = rbuf
            self.closed = False

        def read(self, size):
            size = min(len(self.rbuf), size)
            ret = self.rbuf[:size]
            self.rbuf = self.rbuf[size:]
            return ret

        def close(self):
            self.closed = True

    def fake_os_read(fd, size):
        return fd.read(size)

    def fake_os_close(fd):
        fd.close()

    pipes = []
    for buf in bufs:
        pipe = (FakeFd(buf), FakeFd())
        pipes.append(pipe)

    with mock.patch('storlet_gateway.storlet_runtime.os.pipe') as \
        fake_os_pipe, \
        mock.patch('storlet_gateway.storlet_runtime.os.read',
                   fake_os_read) as fake_os_read,\
        mock.patch('storlet_gateway.storlet_runtime.os.close',
                   fake_os_close) as fake_os_close:
        fake_os_pipe.side_effect = pipes
        yield pipes


class TestRuntimePaths(unittest.TestCase):

    def setUp(self):
        self.account = 'AUTH_0123456789abcdefghijklmnopqrstuv'
        self.scope = '0123456789abc'
        self._initialize()

    def _initialize(self):
        # TODO(takashi): take these values from config file
        base_dir = '/home/docker_device'
        self.script_dir = os.path.join(base_dir, 'scripts')
        self.pipes_dir = os.path.join(base_dir, 'pipes', 'scopes')
        self.storlets_dir = os.path.join(base_dir, 'storlets', 'scopes')
        self.log_dir = os.path.join(base_dir, 'logs', 'scopes')
        self.cache_dir = os.path.join(base_dir, 'cache', 'scopes')

        self.conf = {
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
            os.path.join(self.pipes_dir, self.scope))

    def test_create_host_pipe_prefix(self):
        pipedir = self.paths.host_pipe_prefix()

        # When the directory exists
        with mock.patch('os.path.exists', return_value=True), \
            mock.patch('os.makedirs') as m, \
            mock.patch('os.chmod') as c:
            self.paths.create_host_pipe_prefix()
            self.assertEqual(m.call_count, 0)
            cargs, ckwargs = c.call_args
            # Make sure about the target directory
            self.assertEqual(cargs[0], pipedir)

        # When the directory does not exist
        with mock.patch('os.path.exists', return_value=False), \
            mock.patch('os.makedirs') as m, \
            mock.patch('os.chmod') as c:
            self.paths.create_host_pipe_prefix(),
            self.assertEqual(m.call_count, 1)
            # Make sure about the target directory
            margs, mkwargs = m.call_args
            self.assertEqual(margs[0], pipedir)
            cargs, ckwargs = c.call_args
            self.assertEqual(cargs[0], pipedir)

    def test_host_factory_pipe(self):
        self.assertEqual(
            self.paths.host_factory_pipe(),
            os.path.join(self.pipes_dir, self.scope, 'factory_pipe'))

    def test_host_storlet_pipe(self):
        self.assertEqual(
            self.paths.host_storlet_pipe(self.storlet_id),
            os.path.join(self.pipes_dir, self.scope, self.storlet_id))

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
            os.path.join(self.storlets_dir, self.scope))

    def test_host_storlet(self):
        self.assertEqual(
            self.paths.host_storlet(self.storlet_id),
            os.path.join(self.storlets_dir, self.scope,
                         self.storlet_id))

    def test_slog_path(self):
        with mock.patch('os.path.exists', return_value=True), \
            mock.patch('os.makedirs') as m:
            self.assertEqual(
                self.paths.slog_path(self.storlet_id),
                os.path.join(self.log_dir, self.scope,
                             self.storlet_id))
            self.assertEqual(m.call_count, 0)

        with mock.patch('os.path.exists', return_value=False), \
            mock.patch('os.makedirs') as m:
            self.assertEqual(
                self.paths.slog_path(self.storlet_id),
                os.path.join(self.log_dir, self.scope,
                             self.storlet_id))
            self.assertEqual(m.call_count, 1)

    def test_get_host_storlet_cache_dir(self):
        self.assertEqual(
            self.paths.get_host_storlet_cache_dir(),
            os.path.join(self.cache_dir, self.scope,
                         self.conf['storlet_container']))

    def test_get_host_dependency_cache_dir(self):
        self.assertEqual(
            self.paths.get_host_dependency_cache_dir(),
            os.path.join(self.cache_dir, self.scope,
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
        self.conf = {
            'reseller_prefix': 'AUTH',
            'storlet_container': 'storlet',
            'storlet_dependency': 'dependency',
            'restart_linux_container_timeout': 3,
            'docker_repo': 'localhost:5001'}
        self.account = 'AUTH_0123456789abcdefghijklmnopqrstuv'
        self.sbox = storlet_gateway.storlet_runtime.RunTimeSandbox(
            self.account, self.conf, self.logger)

    def tearDown(self):
        pass

    def test_parse_sandbox_factory_answer(self):
        status, msg = self.sbox._parse_sandbox_factory_answer('True:message')
        self.assertTrue(status)
        self.assertEqual(msg, 'message')

        status, msg = self.sbox._parse_sandbox_factory_answer('False:message')
        self.assertFalse(status)
        self.assertEqual(msg, 'message')

    def _check_all_pipese_closed(self, pipes):
        for _pipe in pipes:
            self.assertTrue(_pipe[0].closed)
            self.assertTrue(_pipe[1].closed)

    def test_ping(self):
        with _mock_os_pipe(['True:OK']) as pipes, _mock_sbus(0):
            self.assertEqual(self.sbox.ping(), 1)
            self._check_all_pipese_closed(pipes)

        with _mock_os_pipe(['False:ERROR']) as pipes, _mock_sbus(-1):
            self.assertEqual(self.sbox.ping(), -1)
            self._check_all_pipese_closed(pipes)

    def test_wait(self):
        with _mock_os_pipe(['True:OK']) as pipes, _mock_sbus(0), \
            mock.patch('storlet_gateway.storlet_runtime.time.sleep') as _s:
            self.sbox.wait()
            self.assertEqual(_s.call_count, 0)
            self._check_all_pipese_closed(pipes)

        with _mock_os_pipe(['False:ERROR', 'True:OK']) as pipes, \
            _mock_sbus(0), \
            mock.patch('storlet_gateway.storlet_runtime.time.sleep') as _s:
            self.sbox.wait()
            self.assertEqual(_s.call_count, 1)
            self._check_all_pipese_closed(pipes)

        # TODO(takashi): should test timeout case

    def test_restart(self):
        with mock.patch('storlet_gateway.storlet_runtime.'
                        'RunTimePaths.create_host_pipe_prefix'), \
            mock.patch('storlet_gateway.storlet_runtime.subprocess.call'):
            _wait = self.sbox.wait

            def dummy_wait_success(*args, **kwargs):
                return 1

            self.sbox.wait = dummy_wait_success
            self.sbox.restart()
            self.sbox.wait = _wait

        with mock.patch('storlet_gateway.storlet_runtime.'
                        'RunTimePaths.create_host_pipe_prefix'), \
            mock.patch('storlet_gateway.storlet_runtime.subprocess.call'):
            _wait = self.sbox.wait

            def dummy_wait_failure(*args, **kwargs):
                raise StorletRuntimeException()

            self.sbox.wait = dummy_wait_failure
            with self.assertRaises(StorletRuntimeException):
                self.sbox.restart()
            self.sbox.wait = _wait


class TestStorletInvocationProtocol(unittest.TestCase):
    def setUp(self):
        self.pipe_path = tempfile.mktemp()
        self.log_file = tempfile.mktemp()

        storlet_request = DockerStorletRequest(
            'test_account', Request.blank('/'), {}, iter(StringIO()))
        self.protocol = \
            storlet_gateway.storlet_runtime.StorletInvocationProtocol(
                storlet_request, self.pipe_path, self.log_file, 1)

    def tearDown(self):
        for path in [self.pipe_path, self.log_file]:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_invocation_protocol(self):
        # os.pipe will be called 4 times
        pipe_called = 4

        with _mock_sbus(0), _mock_os_pipe([''] * pipe_called) as pipes:
            with mock.patch.object(
                    self.protocol, '_wait_for_read_with_timeout'):
                with self.protocol.storlet_logger.activate(), \
                        self.protocol._activate_invocation_descriptors():
                    self.protocol._invoke()

            self.assertEqual(pipe_called, len(pipes))
            pipes = iter(pipes)

            # data write is not directly closed
            # data read is closed by remote
            input_data_read_fd, input_data_write_fd = next(pipes)
            self.assertFalse(input_data_read_fd.closed)
            self.assertFalse(input_data_write_fd.closed)

            # data write is closed but data read is still open
            data_read_fd, data_write_fd = next(pipes)
            self.assertFalse(data_read_fd.closed)
            self.assertTrue(data_write_fd.closed)

            # both execution str fds are closed
            execution_read_fd, execution_write_fd = next(pipes)
            self.assertTrue(execution_read_fd.closed)
            self.assertTrue(execution_write_fd.closed)

            # metadata write fd is closed, metadata read fd is still open.
            metadata_read_fd, metadata_write_fd = next(pipes)
            self.assertFalse(metadata_read_fd.closed)
            self.assertTrue(metadata_write_fd.closed)

            # sanity
            self.assertRaises(StopIteration, next, pipes)

if __name__ == '__main__':
    unittest.main()

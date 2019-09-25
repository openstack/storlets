# Copyright (c) 2015-2016 OpenStack Foundation
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
from contextlib import contextmanager
import errno
import mock
import unittest

from storlets.sbus import command as sbus_cmd
from storlets.sbus.client import SBusResponse
from storlets.sbus.client.exceptions import SBusClientSendError

from storlets.agent.daemon_factory.server import SDaemonError, \
    StorletDaemonFactory
from storlets.agent.common.utils import DEFAULT_PY2, DEFAULT_PY3

from tests.unit import FakeLogger
from tests.unit.agent.common import test_server


class DummyDatagram(object):
    def __init__(self, prms=None):
        self.params = prms or {}


class TestStorletDaemonFactory(unittest.TestCase):
    base_path = 'storlets.agent.daemon_factory.server'
    kill_path = base_path + '.os.kill'
    waitpid_path = base_path + '.os.waitpid'

    @contextmanager
    def _mock_sbus_client(self, method):
        sbusclient_path = self.base_path + '.SBusClient'
        with mock.patch('.'.join([sbusclient_path, method])) as _method:
            yield _method

    def setUp(self):
        self.logger = FakeLogger()
        self.pipe_path = 'path/to/pipe'
        self.container_id = 'contid'
        self.dfactory = StorletDaemonFactory(self.pipe_path, self.logger,
                                             self.container_id)

    def test_get_jvm_args(self):
        dummy_env = {'CLASSPATH': '/default/classpath',
                     'LD_LIBRARY_PATH': '/default/ld/library/path'}
        with mock.patch('storlets.agent.daemon_factory.server.os.environ',
                        dummy_env):
            pargs, env = self.dfactory.get_jvm_args(
                'java', 'path/to/storlet/a', 'Storlet-1.0.jar',
                1, 'path/to/uds/a', 'DEBUG')
            self.assertEqual(
                ['/usr/bin/java', 'org.openstack.storlet.daemon.SDaemon',
                 'Storlet-1.0.jar', 'path/to/uds/a', 'DEBUG', '1',
                 self.container_id],
                pargs)

            self.assertIn('CLASSPATH', env)
            self.assertEqual(
                ['/default/classpath',
                 '/usr/local/lib/storlets/java/logback-classic-1.1.2.jar',
                 '/usr/local/lib/storlets/java/logback-core-1.1.2.jar',
                 '/usr/local/lib/storlets/java/slf4j-api-1.7.7.jar',
                 '/usr/local/lib/storlets/java/json_simple-1.1.jar',
                 '/usr/local/lib/storlets/java/SBusJavaFacade.jar',
                 '/usr/local/lib/storlets/java/SCommon.jar',
                 '/usr/local/lib/storlets/java/SDaemon.jar',
                 '/usr/local/lib/storlets/java/',
                 'path/to/storlet/a'],
                env['CLASSPATH'].split(':'))

            self.assertIn('LD_LIBRARY_PATH', env)
            self.assertEqual(
                ['/default/ld/library/path',
                 '/usr/local/lib/storlets',
                 '/usr/local/lib/storlets/java'],
                env['LD_LIBRARY_PATH'].split(':'))

    def test_get_python_args(self):
        self._test_get_python_args(DEFAULT_PY2, DEFAULT_PY2)
        self._test_get_python_args(2, DEFAULT_PY2)
        self._test_get_python_args(DEFAULT_PY3, DEFAULT_PY3)
        self._test_get_python_args(3, DEFAULT_PY3)

    def _test_get_python_args(self, version, expected):
        dummy_env = {'PYTHONPATH': '/default/pythonpath'}
        with mock.patch('storlets.agent.daemon_factory.server.os.environ',
                        dummy_env):
            pargs, env = self.dfactory.get_python_args(
                'python', 'path/to/storlet', 'test_storlet.TestStorlet',
                1, 'path/to/uds', 'DEBUG', version)
        self.assertEqual(
            ['/usr/bin/python%s' % expected,
             '/usr/local/libexec/storlets/storlets-daemon',
             'test_storlet.TestStorlet',
             'path/to/uds', 'DEBUG', '1', self.container_id],
            pargs)
        self.assertEqual(
            {'PYTHONPATH': '/default/pythonpath:'
                           '/home/swift/test_storlet.TestStorlet'},
            env)

    def test_spawn_subprocess(self):
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a'}

        class FakePopenObject(object):
            def __init__(self, pid):
                self.pid = pid
                self.stderr = mock.MagicMock()

        with mock.patch(self.base_path + '.subprocess.Popen') as popen, \
                mock.patch(self.base_path + '.time.sleep'), \
                mock.patch(self.waitpid_path) as waitpid, \
                self._mock_sbus_client('ping') as ping:
            popen.side_effect = [FakePopenObject(1000),
                                 FakePopenObject(1001)]
            waitpid.return_value = 0, 0
            ping.return_value = SBusResponse(True, 'OK')
            self.dfactory.spawn_subprocess(
                ['arg0', 'argv1', 'argv2'],
                {'envk0': 'envv0'}, 'storleta')
            self.assertEqual((1000, 1), waitpid.call_args[0])
            self.assertEqual({'storleta': 1000},
                             self.dfactory.storlet_name_to_pid)

        with mock.patch(self.base_path + '.subprocess.Popen') as popen, \
                mock.patch(self.base_path + '.time.sleep'), \
                mock.patch(self.waitpid_path) as waitpid, \
                self._mock_sbus_client('ping') as ping:
            popen.side_effect = [FakePopenObject(1000),
                                 FakePopenObject(1001)]
            waitpid.return_value = 0, 0
            ping.return_value = SBusResponse(False, 'NG')
            with self.assertRaises(SDaemonError):
                self.dfactory.spawn_subprocess(
                    ['arg0', 'argv1', 'argv2'],
                    {'envk0': 'envv0'}, 'storleta')
            self.assertEqual((1000, 1), waitpid.call_args[0])
            self.assertEqual({'storleta': 1000},
                             self.dfactory.storlet_name_to_pid)

        with mock.patch(self.base_path + '.subprocess.Popen') as popen, \
                mock.patch(self.base_path + '.time.sleep'), \
                mock.patch(self.waitpid_path) as waitpid:
            popen.side_effect = [FakePopenObject(1000),
                                 FakePopenObject(1001)]
            waitpid.return_value = 1000, -1
            with self.assertRaises(SDaemonError):
                self.dfactory.spawn_subprocess(
                    ['arg0', 'argv1', 'argv2'],
                    {'envk0': 'envv0'}, 'storleta')
            self.assertEqual((1000, 1), waitpid.call_args[0])

        with mock.patch(self.base_path + '.subprocess.Popen') as popen:
            popen.side_effect = OSError()
            with self.assertRaises(SDaemonError):
                self.dfactory.spawn_subprocess(
                    ['arg0', 'argv1', 'argv2'],
                    {'envk0': 'envv0'}, 'storleta')

    def test_wait_for_daemon_to_initialize(self):
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a'}

        with self._mock_sbus_client('ping') as ping, \
                mock.patch(self.base_path + '.time.sleep'):
            ping.return_value = SBusResponse(True, 'OK')
            self.assertTrue(
                self.dfactory.wait_for_daemon_to_initialize('storleta'))
            self.assertEqual(1, ping.call_count)

        with self._mock_sbus_client('ping') as ping, \
                mock.patch(self.base_path + '.time.sleep'):
            ping.return_value = SBusResponse(False, 'NG')
            self.assertFalse(
                self.dfactory.wait_for_daemon_to_initialize('storleta'))
            self.assertEqual(
                self.dfactory.NUM_OF_TRIES_PINGING_STARTING_DAEMON,
                ping.call_count)

        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self._mock_sbus_client('ping') as ping, \
                mock.patch(self.base_path + '.time.sleep'):
            ping.side_effect = SBusClientSendError()
            self.assertFalse(
                self.dfactory.wait_for_daemon_to_initialize('storleta'))
            self.assertEqual(
                self.dfactory.NUM_OF_TRIES_PINGING_STARTING_DAEMON,
                ping.call_count)

    def test_process_start_daemon(self):
        # Not running
        self.dfactory.storlet_name_to_pid = {}
        self.dfactory.storlet_name_to_pipe_name = {}

        class FakePopenObject(object):
            def __init__(self, pid):
                self.pid = pid
                self.stderr = mock.MagicMock()

        with mock.patch(self.base_path + '.subprocess.Popen') as popen, \
                mock.patch(self.base_path + '.time.sleep'), \
                mock.patch(self.waitpid_path) as waitpid, \
                self._mock_sbus_client('ping') as ping:
            popen.side_effect = [FakePopenObject(1000),
                                 FakePopenObject(1001)]
            waitpid.return_value = 0, 0
            ping.return_value = SBusResponse(True, 'OK')
            self.assertTrue(self.dfactory.process_start_daemon(
                'java', 'path/to/storlet/a', 'storleta', 1, 'path/to/uds/a',
                'TRACE'))
            self.assertEqual({'storleta': 'path/to/uds/a'},
                             self.dfactory.storlet_name_to_pipe_name)

        # Already running
        self.dfactory.storlet_name_to_pid = {'storleta': 1000}
        self.dfactory.storlet_name_to_pipe_name = {'storleta': 'path/to/uds/a'}
        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 0, 0
            self.assertFalse(self.dfactory.process_start_daemon(
                'java', 'path/to/storlet/a', 'storleta', 1, 'path/to/uds/a',
                'TRACE'))

        # Unsupported language
        with self.assertRaises(SDaemonError):
            self.dfactory.process_start_daemon(
                'foo', 'path/to/storlet/a', 'storleta', 1, 'path/to/uds/a',
                'TRACE')

    def test_get_process_status_by_name(self):
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 0, 0
            self.assertTrue(
                self.dfactory.get_process_status_by_name('storleta'))
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual((1000, 1), waitpid.call_args[0])

        self.assertFalse(
            self.dfactory.get_process_status_by_name('storletc'))

    def test_get_process_status_by_pid(self):
        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 0, 0
            self.assertTrue(
                self.dfactory.get_process_status_by_pid(1000, 'storleta'))
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual((1000, 1), waitpid.call_args[0])

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 1000, 0
            self.assertFalse(
                self.dfactory.get_process_status_by_pid(1000, 'storleta'))
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual((1000, 1), waitpid.call_args[0])

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = OSError(errno.ESRCH, '')
            self.assertFalse(
                self.dfactory.get_process_status_by_pid(1000, 'storleta'))
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual((1000, 1), waitpid.call_args[0])

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = OSError(errno.EPERM, '')
            exc_pattern = ('^No permission to access the storlet daemon'
                           ' storleta$')
            with self.assertRaisesRegexp(SDaemonError, exc_pattern):
                self.dfactory.get_process_status_by_pid(1000, 'storleta')
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual((1000, 1), waitpid.call_args[0])

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = OSError()
            exc_pattern = '^Unknown error$'
            with self.assertRaisesRegexp(SDaemonError, exc_pattern):
                self.dfactory.get_process_status_by_pid(1000, 'storleta')
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual((1000, 1), waitpid.call_args[0])

    def test_process_kill(self):
        # Success
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 1000, 0
            self.assertEqual((1000, 0),
                             self.dfactory.process_kill('storleta'))
            self.assertEqual(1, kill.call_count)
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual({'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # When failed to send kill to the storlet daemon
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            kill.side_effect = OSError()
            with self.assertRaises(SDaemonError):
                self.dfactory.process_kill('storleta')
            self.assertEqual(1, kill.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # When failed to wait
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = OSError()
            with self.assertRaises(SDaemonError):
                self.dfactory.process_kill('storleta')
            self.assertEqual(1, kill.call_count)
            self.assertEqual(1, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # if the storlet daemon is not recognised
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            with self.assertRaises(SDaemonError):
                self.dfactory.process_kill('storletc')
            self.assertEqual(0, kill.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

    def test_process_kill_all(self):
        # Success
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = [(1000, 0), (1001, 0)]
            self.dfactory.process_kill_all()
            self.assertEqual(2, kill.call_count)
            self.assertEqual(2, waitpid.call_count)
            self.assertEqual({}, self.dfactory.storlet_name_to_pid)

        # Success (no processes)
        self.dfactory.storlet_name_to_pid = {}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            self.dfactory.process_kill_all()
            self.assertEqual(0, kill.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({}, self.dfactory.storlet_name_to_pid)

        # Failure (try_all = True)
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            kill.side_effect = OSError()
            exc_pattern = '^Failed to stop some storlet daemons: .*'
            with self.assertRaisesRegexp(SDaemonError, exc_pattern) as e:
                self.dfactory.process_kill_all()
            self.assertIn('storleta', str(e.exception))
            self.assertIn('storletb', str(e.exception))
            self.assertEqual(2, kill.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # Failure (try_all = False)
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path) as waitpid:
            kill.side_effect = OSError()
            exc_pattern = ('^Failed to send kill signal to the storlet daemon '
                           'storlet[a-b]$')
            with self.assertRaisesRegexp(SDaemonError, exc_pattern):
                self.dfactory.process_kill_all(False)
            self.assertEqual(1, kill.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

    def test_shutdown_all_processes(self):
        # Success
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path):
            halt.return_value = SBusResponse(True, 'OK')
            terminated = self.dfactory.shutdown_all_processes()
            self.assertEqual(2, len(terminated))
            self.assertIn('storleta', terminated)
            self.assertIn('storletb', terminated)
            self.assertEqual({},
                             self.dfactory.storlet_name_to_pid)

        # Failure (try_all = True)
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'patha', 'storletb': 'pathb'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path) as waitpid:
            halt.side_effect = SBusClientSendError()
            exc_pattern = '^Failed to shutdown some storlet daemons: .*'
            with self.assertRaisesRegexp(SDaemonError, exc_pattern) as e:
                self.dfactory.shutdown_all_processes()
            self.assertIn('storleta', str(e.exception))
            self.assertIn('storletb', str(e.exception))
            self.assertEqual(2, halt.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # Failure (try_all = False)
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'patha', 'storletb': 'pathb'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path) as waitpid:
            halt.side_effect = SBusClientSendError()
            exc_pattern = ('^Failed to send halt command to the storlet '
                           'daemon storlet[a-b]$')
            with self.assertRaisesRegexp(SDaemonError, exc_pattern):
                self.dfactory.shutdown_all_processes(False)
            self.assertEqual(1, halt.call_count)
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

    def test_shutdown_process(self):
        # Success
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path):
            halt.return_value = SBusResponse(True, 'OK')
            self.dfactory.shutdown_process('storleta')
            self.assertEqual({'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # Failed to send a command to the storlet daemon
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path) as waitpid:
            halt.side_effect = SBusClientSendError()
            with self.assertRaises(SDaemonError):
                self.dfactory.shutdown_process('storleta')
            self.assertEqual(0, waitpid.call_count)
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # Failed to wait
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path) as waitpid:
            halt.return_value = SBusResponse(True, 'OK')
            waitpid.side_effect = OSError()
            with self.assertRaises(SDaemonError):
                self.dfactory.shutdown_process('storleta')
            self.assertEqual({'storleta': 1000, 'storletb': 1001},
                             self.dfactory.storlet_name_to_pid)

        # If the storlet is not found in pid mapping
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self.assertRaises(SDaemonError):
            self.dfactory.shutdown_process('storletc')

    def test_start_daemon(self):
        prms = {'daemon_language': 'java',
                'storlet_path': 'path/to/storlet/a',
                'storlet_name': 'storleta',
                'pool_size': 1,
                'uds_path': 'path/to/uds/a',
                'log_level': 'TRACE'}
        # Not running
        self.dfactory.storlet_name_to_pid = {}
        self.dfactory.storlet_name_to_pipe_name = {}

        class FakePopenObject(object):
            def __init__(self, pid):
                self.pid = pid
                self.stderr = mock.MagicMock()

        with mock.patch(self.base_path + '.subprocess.Popen') as popen, \
                mock.patch(self.base_path + '.time.sleep'), \
                mock.patch(self.waitpid_path) as waitpid, \
                self._mock_sbus_client('ping') as ping, \
                self._mock_sbus_client('start_daemon') as start_daemon:
            popen.side_effect = [FakePopenObject(1000),
                                 FakePopenObject(1001)]
            waitpid.return_value = 0, 0
            ping.return_value = SBusResponse(True, 'OK')
            start_daemon.return_value = SBusResponse(True, 'OK')
            ret = self.dfactory.start_daemon(DummyDatagram(prms))
            self.assertTrue(ret.status)
            self.assertEqual('OK', ret.message)
            self.assertTrue(ret.iterable)

        # Already running
        self.dfactory.storlet_name_to_pid = {'storleta': 1000}
        self.dfactory.storlet_name_to_pipe_name = {'storleta': 'path/to/uds/a'}
        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 0, 0
            ret = self.dfactory.start_daemon(DummyDatagram(prms))
            self.assertTrue(ret.status)
            self.assertEqual('storleta is already running', ret.message)
            self.assertTrue(ret.iterable)

        # Unsupported language
        prms['daemon_language'] = 'foo'
        ret = self.dfactory.start_daemon(DummyDatagram(prms))
        self.assertFalse(ret.status)
        self.assertEqual('Got unsupported daemon language: foo', ret.message)
        self.assertTrue(ret.iterable)

    def test_stop_daemon(self):
        # Success
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000}
        with mock.patch(self.kill_path), \
                mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 1000, 0
            resp = self.dfactory.stop_daemon(
                DummyDatagram({'storlet_name': 'storleta'}))
            self.assertTrue(resp.status)
            self.assertEqual('Storlet storleta, PID = 1000, ErrCode = 0',
                             resp.message)
            self.assertTrue(resp.iterable)

        # Failure
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000}
        with mock.patch(self.kill_path) as kill, \
                mock.patch(self.waitpid_path):
            kill.side_effect = OSError('ERROR')
            resp = self.dfactory.stop_daemon(
                DummyDatagram({'storlet_name': 'storleta'}))
            self.assertFalse(resp.status)
            self.assertEqual(
                'Failed to send kill signal to the storlet daemon storleta',
                resp.message)
            self.assertTrue(resp.iterable)

    def test_daemon_status(self):
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 0, 0
            resp = self.dfactory.daemon_status(
                DummyDatagram({'storlet_name': 'storleta'}))
            self.assertTrue(resp.status)
            self.assertEqual('The storlet daemon storleta seems to be OK',
                             resp.message)
            self.assertTrue(resp.iterable)

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.return_value = 1000, 0
            resp = self.dfactory.daemon_status(
                DummyDatagram({'storlet_name': 'storleta'}))
            self.assertFalse(resp.status)
            self.assertEqual('No running storlet daemons for storleta',
                             resp.message)
            self.assertTrue(resp.iterable)

        with mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = OSError()
            resp = self.dfactory.daemon_status(
                DummyDatagram({'storlet_name': 'storleta'}))
            self.assertFalse(resp.status)
            self.assertEqual('Unknown error', resp.message)
            self.assertTrue(resp.iterable)

    def test_halt(self):
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        self.dfactory.storlet_name_to_pipe_name = \
            {'storleta': 'path/to/uds/a', 'storletb': 'path/to/uds/b'}
        with self._mock_sbus_client('halt') as halt, \
                mock.patch(self.waitpid_path):
            halt.return_value = SBusResponse(True, 'OK')
            resp = self.dfactory.halt(DummyDatagram())
            self.assertTrue(resp.status)
            self.assertIn('storleta: terminated', resp.message)
            self.assertIn('storletb: terminated', resp.message)
            self.assertFalse(resp.iterable)

    def test_stop_daemons(self):
        # Success
        self.dfactory.storlet_name_to_pid = \
            {'storleta': 1000, 'storletb': 1001}
        with mock.patch(self.kill_path), \
                mock.patch(self.waitpid_path) as waitpid:
            waitpid.side_effect = [(1000, 0), (1001, 0)]
            resp = self.dfactory.stop_daemons(DummyDatagram())
            self.assertTrue(resp.status)
            self.assertEqual('OK', resp.message)
            self.assertFalse(resp.iterable)


class TestSBusServerMain(test_server.TestSBusServerMain):

    def _get_test_server(self):
        return StorletDaemonFactory(self.sbus_path, self.logger, 'contid')

    def test_main_loop_successful_stop(self):
        # SBUS_CMD_HALT is for working to stop requested from
        # storlet_middleware
        self._test_main_loop_stop(sbus_cmd.SBUS_CMD_HALT)


if __name__ == '__main__':
    unittest.main()

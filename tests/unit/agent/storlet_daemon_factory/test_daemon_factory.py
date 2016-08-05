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

import logging
import unittest
from six import StringIO

from SBusPythonFacade import SBusStorletCommand

from tests.unit.swift import FakeLogger
from storlet_daemon_factory.daemon_factory import CommandResponse, \
    CommandSuccess, CommandFailure, DaemonFactory, start_logger


class TestCommandResponse(unittest.TestCase):
    def setUp(self):
        pass

    def test_init(self):
        resp = CommandResponse(True, 'ok')
        self.assertTrue(resp.status)
        self.assertEqual('ok', resp.message)
        self.assertTrue(resp.iterable)

        resp = CommandResponse(False, 'error', False)
        self.assertFalse(resp.status)
        self.assertEqual('error', resp.message)
        self.assertFalse(resp.iterable)

    def test_report_message(self):
        resp = CommandResponse(True, 'msg', True)
        self.assertEqual('True: msg', resp.report_message)


class TestCommandSuccess(unittest.TestCase):
    def setUp(self):
        pass

    def test_init(self):
        resp = CommandSuccess('ok')
        self.assertTrue(resp.status)
        self.assertEqual('ok', resp.message)
        self.assertTrue(resp.iterable)


class TestCommandFailure(unittest.TestCase):
    def setUp(self):
        pass

    def test_init(self):
        resp = CommandFailure('error')
        self.assertFalse(resp.status)
        self.assertEqual('error', resp.message)
        self.assertTrue(resp.iterable)


class TestLogger(unittest.TestCase):
    def setUp(self):
        pass

    def test_start_logger(self):
        sio = StringIO()
        logger = logging.getLogger('CONT #abcdef: test')
        logger.addHandler(logging.StreamHandler(sio))

        # set log level as INFO
        logger = start_logger('test', 'INFO', 'abcdef')
        self.assertEqual(logging.INFO, logger.level)
        # INFO message is recorded with INFO leg level
        logger.info('test1')
        self.assertEqual(sio.getvalue(), 'test1\n')
        # DEBUG message is not recorded with INFO leg level
        logger.debug('test2')
        self.assertEqual(sio.getvalue(), 'test1\n')

        # set log level as DEBUG
        logger = start_logger('test', 'DEBUG', 'abcdef')
        self.assertEqual(logging.DEBUG, logger.level)
        # DEBUG message is recorded with DEBUG leg level
        logger.debug('test3')
        self.assertEqual(sio.getvalue(), 'test1\ntest3\n')

        # If the level parameter is unkown, use ERROR as log level
        logger = start_logger('test', 'foo', 'abcdef')
        self.assertEqual(logging.ERROR, logger.level)


class TestDaemonFactory(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.pipe_path = 'path/to/pipe'
        self.dfactory = DaemonFactory(self.pipe_path, self.logger)

    def test_get_handler(self):
        # start daemon
        self.assertEqual(
            self.dfactory.start_daemon,
            self.dfactory.get_handler(
                SBusStorletCommand.SBUS_CMD_START_DAEMON))
        # stop daemon
        self.assertEqual(
            self.dfactory.stop_daemon,
            self.dfactory.get_handler(
                SBusStorletCommand.SBUS_CMD_STOP_DAEMON))
        # daemon status
        self.assertEqual(
            self.dfactory.daemon_status,
            self.dfactory.get_handler(
                SBusStorletCommand.SBUS_CMD_DAEMON_STATUS))
        # stop daemons
        self.assertEqual(
            self.dfactory.stop_daemons,
            self.dfactory.get_handler(
                SBusStorletCommand.SBUS_CMD_STOP_DAEMONS))
        # halt
        self.assertEqual(
            self.dfactory.halt,
            self.dfactory.get_handler(
                SBusStorletCommand.SBUS_CMD_HALT))
        # ping
        self.assertEqual(
            self.dfactory.ping,
            self.dfactory.get_handler(
                SBusStorletCommand.SBUS_CMD_PING))
        # invalid
        with self.assertRaises(ValueError):
            self.dfactory.get_handler('FOO')
        # unkown
        with self.assertRaises(ValueError):
            self.dfactory.get_handler('SBUS_CMD_UNKOWN')
        # not command handler
        with self.assertRaises(ValueError):
            self.dfactory.get_handler('SBUS_CMD_GET_JVM_ARGS')


if __name__ == '__main__':
    unittest.main()

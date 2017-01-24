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

import json
import mock
import os
import unittest
import errno
from contextlib import contextmanager

from storlets.sbus.client.exceptions import SBusClientSendError, \
    SBusClientMalformedResponse
from storlets.sbus.client import SBusClient


@contextmanager
def _mock_sbus(send_status=0):
    with mock.patch('storlets.sbus.client.SBus.send') as fake_send:
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
            if self.closed:
                raise OSError(errno.EBADF, os.strerror(errno.EBADF))
            self.closed = True

    def fake_os_read(fd, size):
        return fd.read(size)

    def fake_os_close(fd):
        fd.close()

    pipes = [(FakeFd(buf), FakeFd()) for buf in bufs]
    pipe_generator = iter(pipes)

    def mock_os_pipe():
        try:
            return next(pipe_generator)
        except StopIteration:
            raise AssertionError('pipe called more than expected')

    with mock.patch('storlets.sbus.client.os.pipe', mock_os_pipe), \
            mock.patch('storlets.sbus.client.os.read', fake_os_read), \
            mock.patch('storlets.sbus.client.os.close', fake_os_close):
        yield pipes


class TestSBusClient(unittest.TestCase):
    def setUp(self):
        self.pipe_path = 'pipe_path'
        self.client = SBusClient(self.pipe_path, 4)

    def test_parse_response(self):
        raw_resp = json.dumps({'status': True, 'message': 'OK'})
        resp = self.client._parse_response(raw_resp)
        self.assertTrue(resp.status)
        self.assertEqual('OK', resp.message)

        raw_resp = json.dumps({'status': False, 'message': 'ERROR'})
        resp = self.client._parse_response(raw_resp)
        self.assertFalse(resp.status)
        self.assertEqual('ERROR', resp.message)

        raw_resp = json.dumps({'status': True, 'message': 'Sample:Message'})
        resp = self.client._parse_response(raw_resp)
        self.assertTrue(resp.status)
        self.assertEqual('Sample:Message', resp.message)

        with self.assertRaises(SBusClientMalformedResponse):
            self.client._parse_response('Foo')

        raw_resp = json.dumps({'status': True})
        with self.assertRaises(SBusClientMalformedResponse):
            self.client._parse_response(raw_resp)

        raw_resp = json.dumps({'message': 'foo'})
        with self.assertRaises(SBusClientMalformedResponse):
            self.client._parse_response(raw_resp)

    def _check_all_pipes_closed(self, pipes):
        # Make sure that pipes are not empty
        self.assertGreater(len(pipes), 0)

        for _pipe in pipes:
            self.assertTrue(_pipe[0].closed)
            self.assertTrue(_pipe[1].closed)

    def _test_service_request(self, method, *args, **kwargs):
        raw_resp = json.dumps({'status': True, 'message': 'OK'})
        with _mock_os_pipe([raw_resp]) as pipes, _mock_sbus(0):
            resp = method(*args, **kwargs)
            self.assertTrue(resp.status)
            self.assertEqual('OK', resp.message)
            self._check_all_pipes_closed(pipes)

        raw_resp = json.dumps({'status': False, 'message': 'ERROR'})
        with _mock_os_pipe([raw_resp]) as pipes, _mock_sbus(0):
            resp = method(*args, **kwargs)
            self.assertFalse(resp.status)
            self.assertEqual('ERROR', resp.message)
            self._check_all_pipes_closed(pipes)

        raw_resp = json.dumps({'status': True, 'message': 'OK'})
        with _mock_os_pipe([raw_resp]) as pipes, _mock_sbus(-1):
            with self.assertRaises(SBusClientSendError):
                method(*args, **kwargs)
            self._check_all_pipes_closed(pipes)

        # TODO(takashi): Add IOError case

        with _mock_os_pipe(['Foo']) as pipes, _mock_sbus(0):
            with self.assertRaises(SBusClientMalformedResponse):
                method(*args, **kwargs)
            self._check_all_pipes_closed(pipes)

    def test_ping(self):
        self._test_service_request(self.client.ping)

    def test_start_daemon(self):
        self._test_service_request(
            self.client.start_daemon, 'java', 'path/to/storlet',
            'storleta', 'path/to/uds', 'INFO', '10', '11')

    def test_stop_daemon(self):
        self._test_service_request(self.client.stop_daemon, 'storleta')

    def test_stop_daemons(self):
        self._test_service_request(self.client.stop_daemons)

    def test_halt(self):
        self._test_service_request(self.client.halt)

    def test_daemon_status(self):
        self._test_service_request(self.client.daemon_status, 'storleta')

    def test_cancel(self):
        self._test_service_request(self.client.cancel, 'taskid')


if __name__ == '__main__':
    unittest.main()

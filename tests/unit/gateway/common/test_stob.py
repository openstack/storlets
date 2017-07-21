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

from contextlib import contextmanager
import mock
import os
import tempfile
import unittest
from storlets.gateway.common.stob import FileDescriptorIterator


class TestFileDescriptorIterator(unittest.TestCase):

    def setUp(self):
        self.timeout = 10
        self.content = b'aaaa\nbbbb\ncccc\n'

        # TODO(takashi): TemporaryFile may be safer, but causes OS Error in
        #                close in IterLike.__del__
        self.fd, fname = tempfile.mkstemp()
        os.unlink(fname)
        os.write(self.fd, self.content)
        self._reset_fd()
        self.iter_like = FileDescriptorIterator(
            self.fd, self.timeout, None)

    def tearDown(self):
        pass

    def _fake_select(self, r, w, x, timeout=0):
        return r, w, x

    def _reset_fd(self):
        os.lseek(self.fd, 0, os.SEEK_SET)

    @contextmanager
    def _mock_select(self):
        # TODO(takashi): This is needed to avoid PermissionError in UT
        with mock.patch('storlets.gateway.common.stob.select.select',
                        self._fake_select):
            yield

    def test_read_with_timeout(self):
        self.assertEqual(
            b'aaaa\nb', self.iter_like.read_with_timeout(6))
        self.assertEqual(
            b'bbb\ncc', self.iter_like.read_with_timeout(6))
        self.assertEqual(
            b'cc\n', self.iter_like.read_with_timeout(6))
        self.assertEqual(
            b'', self.iter_like.read_with_timeout(6))

    def test_next(self):
        with self._mock_select():
            self.assertEqual(b'aaaa\nb', self.iter_like.next(6))
            self.assertEqual(b'bbb\ncc', self.iter_like.next(6))
            self.assertEqual(b'cc\n', self.iter_like.next(6))
            with self.assertRaises(StopIteration):
                self.iter_like.next(6)
        self._reset_fd()

        with self._mock_select():
            # if size > content length
            self.assertEqual(b'aaaa\nbbbb\ncccc\n',
                             self.iter_like.next(50))
            with self.assertRaises(StopIteration):
                self.iter_like.next(50)

    def test_read(self):
        with self._mock_select():
            self.assertEqual(b'aaaa\nb', self.iter_like.read(6))
            self.assertEqual(b'bbb\ncc', self.iter_like.read(6))
            self.assertEqual(b'cc\n', self.iter_like.read(6))
            with self.assertRaises(StopIteration):
                self.iter_like.next(6)

    def test_readline(self):
        with self._mock_select():
            # if size = -1
            self.assertEqual(b'aaaa\n', self.iter_like.readline())

            # if size < line length
            self.assertEqual(b'bb', self.iter_like.readline(2))

            # read remaining chars in line
            self.assertEqual(b'bb\n', self.iter_like.readline())

            # if size > line length
            self.assertEqual(b'cccc\n', self.iter_like.readline(100))
            with self.assertRaises(StopIteration):
                self.iter_like.readline()

    def test_readlines(self):
        with self._mock_select():
            self.assertEqual(
                [b'aaaa\n', b'bbbb\n', b'cccc\n'],
                self.iter_like.readlines())
        self._reset_fd()

        with self._mock_select():
            self.assertEqual(
                [b'aaaa\n', b'bb'],
                self.iter_like.readlines(7))


if __name__ == '__main__':
    unittest.main()

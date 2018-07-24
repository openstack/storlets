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
import os
import tempfile
import unittest
from storlets.agent.daemon.files import StorletFile, StorletInputFile, \
    StorletRangeInputFile, StorletOutputFile


class TestStorletFile(unittest.TestCase):
    def setUp(self):
        self.fd, self.fname = tempfile.mkstemp()
        self._prepare_file()
        self.sfile = self._create_file()

    def _prepare_file(self):
        pass

    def tearDown(self):
        try:
            # Make sure that fd is closed
            os.close(self.fd)
        except OSError:
            pass
        os.unlink(self.fname)

    def _create_file(self):
        return StorletFile(self.fd)

    def test_closed(self):
        self.assertFalse(self.sfile.closed)
        self.sfile.close()
        self.assertTrue(self.sfile.closed)

    def test_contextmanager(self):
        with self.sfile as sfile:
            self.assertFalse(sfile.closed)
        self.assertTrue(sfile.closed)


class TestStorletOutputFile(TestStorletFile):

    def setUp(self):
        self.metadata = {'key1': 'value1'}
        self.md_fd, self.md_fname = tempfile.mkstemp()
        super(TestStorletOutputFile, self).setUp()

    def tearDown(self):
        try:
            # Make sure that fd is closed
            os.close(self.md_fd)
        except OSError:
            pass
        os.unlink(self.md_fname)
        super(TestStorletOutputFile, self).tearDown()

    def _create_file(self):
        return StorletOutputFile(self.md_fd, self.fd)

    def test_set_metadata(self):
        with self.sfile as sfile:
            sfile.set_metadata(self.metadata)
            self.assertEqual(self.metadata, sfile.get_metadata())

        with open(self.md_fname, 'r') as f:
            self.assertEqual(self.metadata,
                             json.loads(f.read()))

    def test_set_metadata_twice(self):
        with self.sfile as sfile:
            sfile.set_metadata(self.metadata)
            with self.assertRaises(IOError):
                sfile.set_metadata({})

    def test_get_metadata_before_set(self):
        with self.sfile as sfile:
            with self.assertRaises(IOError):
                sfile.get_metadata()

    def test_write_before_set_metadata(self):
        with self.sfile as sfile:
            with self.assertRaises(IOError):
                sfile.write('foo')

    def test_write(self):
        with self.sfile as sfile:
            sfile.set_metadata({})
            sfile.write('testing')
            sfile.flush()

        with open(self.fname, 'r') as f:
            self.assertEqual('testing', f.read())

    def test_writelines(self):
        with self.sfile as sfile:
            sfile.set_metadata({})
            sfile.writelines(['tes', 'ti', 'ng'])
            sfile.flush()

        with open(self.fname, 'r') as f:
            self.assertEqual('testing', f.read())


class TestStorletInputFile(TestStorletFile):

    def setUp(self, content=None):
        self.content = content or b'abcd\nefg\nhi\nj'
        self.metadata = {'key1': 'value1'}
        super(TestStorletInputFile, self).setUp()

    def _prepare_file(self):
        with open(self.fname, 'wb') as f:
            f.write(self.content)

    def _create_file(self):
        return StorletInputFile(self.metadata, self.fd)

    def test_read(self):
        self.assertEqual(b'abcd\nefg\nhi\nj', self.sfile.read())

    def test_read_size(self):
        expects = [b'abc', b'd\ne', b'fg\n', b'hi\n', b'j', b'']
        for expect in expects:
            self.assertEqual(expect, self.sfile.read(3))

    def test_readline(self):
        expects = [b'abcd\n', b'efg\n', b'hi\n', b'j', b'']
        for expect in expects:
            self.assertEqual(expect, self.sfile.readline())

    def test_readline_size(self):
        expects = [b'abc', b'd\n', b'efg', b'\n', b'hi\n', b'j', b'']
        for expect in expects:
            self.assertEqual(expect, self.sfile.readline(3))

    def test_readlines(self):
        self.assertEqual([b'abcd\n', b'efg\n', b'hi\n', b'j'],
                         self.sfile.readlines())

    def test_iter(self):
        buf = b''
        for rbuf in self.sfile:
            buf += rbuf
        self.assertEqual(b'abcd\nefg\nhi\nj', buf)

    def test_get_metadata(self):
        self.assertEqual(self.metadata, self.sfile.get_metadata())

    def test_set_metadata(self):
        with self.assertRaises(NotImplementedError):
            self.sfile.set_metadata({})


class TestStorletRangeInputFile(TestStorletInputFile):

    def setUp(self):
        content = b'012\n345\nabcd\nefg\nhi\nj67\n8'
        self.start = 8
        self.end = 21
        super(TestStorletRangeInputFile, self).setUp(content)

    def _create_file(self):
        return StorletRangeInputFile(self.metadata, self.fd, self.start,
                                     self.end)


if __name__ == '__main__':
    unittest.main()

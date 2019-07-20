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

import os
import shutil
import tempfile
import unittest
from storlets.gateway.common.exceptions import StorletLoggerError
from storlets.gateway.common.logger import StorletLogger


class TestStorletLogger(unittest.TestCase):

    def setUp(self):
        self.log_dir = tempfile.mkdtemp()
        self.log_path = tempfile.mktemp(dir=self.log_dir)
        self.logger = StorletLogger(self.log_path)

    def tearDown(self):
        if os.path.isdir(self.log_dir):
            shutil.rmtree(self.log_dir)

    def test_open_close(self):
        self.assertIsNone(self.logger._file)
        self.logger.open()
        self.assertIsNotNone(self.logger._file)
        self.assertTrue(os.path.isfile(self.log_path))
        self.logger.close()
        self.assertIsNone(self.logger._file)

        # Make sure that log_dir is deleted
        shutil.rmtree(self.log_dir)

        # As log_dir does not exists, open should create it
        self.logger.open()
        self.assertIsNotNone(self.logger._file)
        self.assertTrue(os.path.isdir(self.log_dir))
        self.assertTrue(os.path.isfile(self.log_path))
        self.logger.close()
        self.assertIsNone(self.logger._file)

        # opened twice
        self.logger.open()
        with self.assertRaises(StorletLoggerError):
            self.logger.open()
        self.logger.close()

        # closed twice
        self.logger.open()
        self.logger.close()
        with self.assertRaises(StorletLoggerError):
            self.logger.close()

    def test_getfd(self):
        self.assertIsNone(self.logger.getfd())
        self.logger.open()
        self.assertIsNotNone(self.logger.getfd())
        self.logger.close()

    def test_getsize(self):
        self.logger.open()
        self.logger._file.write('a' * 1024)
        self.logger.close()
        self.assertEqual(1024, self.logger.getsize())

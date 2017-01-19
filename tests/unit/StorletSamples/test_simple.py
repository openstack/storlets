# Copyright (c) 2015, 2016 OpenStack Foundation.
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

from unittest import TestCase
from storlet_samples.simple.simple import SimpleStorlet
from storlets.tools.testtools import FakeStorletFileIn, FakeStorletFileOut
from tests.unit import FakeLogger
import unittest


class TestSimpleStorlet(TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def test_simple_storlet(self):
        simple_storlet = SimpleStorlet(self.logger)
        input_string = 'abcdefghijklmonp'
        store_in = [FakeStorletFileIn(input_string, {})]
        store_out = [FakeStorletFileOut()]
        params = {}
        self.assertIsNone(simple_storlet(store_in, store_out, params))
        # SimpleStorlet sets metadata {'test': 'simple'}
        self.assertEqual({'test': 'simple'}, store_out[0]._metadata)
        self.assertEqual(input_string, store_out[0].read())
        self.assertTrue(store_in[0].closed)
        self.assertTrue(store_out[0].closed)


if __name__ == '__main__':
    unittest.main()

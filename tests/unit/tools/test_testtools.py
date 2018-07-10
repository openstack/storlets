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

from storlets.tools.testtools import FakeStorletFileIn, FakeStorletFileOut


class TestTestTools(TestCase):
    def test_fake_storlet_file_in(self):
        input_string = 'abcdefghijklmonp'
        input_metadata = {'foo': 'bar'}
        fake_storlet_in = FakeStorletFileIn(input_string, input_metadata)
        self.assertEqual(input_string, fake_storlet_in.read())
        self.assertEqual(input_metadata, fake_storlet_in.get_metadata())

        fake_storlet_in.close()
        self.assertTrue(fake_storlet_in.closed)

    def test_fake_storlet_file_out(self):
        out_string = 'abcdefghijklmonp'
        fake_storlet_out = FakeStorletFileOut()
        fake_storlet_out.write(out_string)
        self.assertEqual(out_string, fake_storlet_out.read())
        fake_storlet_out.write(out_string)
        self.assertEqual(out_string * 2, fake_storlet_out.read())

        self.assertIsNone(fake_storlet_out._metadata)
        fake_storlet_out.set_metadata({'test': 'tester'})
        self.assertEqual({'test': 'tester'}, fake_storlet_out._metadata)

        fake_storlet_out.close()
        self.assertTrue(fake_storlet_out.closed)

    def test_fake_storlet_file_out_set_metadata_twice_will_cause_error(self):
        fake_storlet_out = FakeStorletFileOut()
        # first call, it's ok
        fake_storlet_out.set_metadata({})
        # second call will raise an exception
        with self.assertRaises(IOError) as cm:
            fake_storlet_out.set_metadata({})
        self.assertEqual(
            "Sending metadata twice is not allowed",
            cm.exception.args[0])

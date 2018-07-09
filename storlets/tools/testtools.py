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

from six.moves import StringIO


class FakeStorletFile(object):
    def __init__(self):
        self._call_closed = False

    def close(self):
        self._call_closed = True

    @property
    def closed(self):
        return self._call_closed


class FakeStorletFileIn(FakeStorletFile):
    def __init__(self, input_string, metadata):
        super(FakeStorletFileIn, self).__init__()
        self._input_string = StringIO(input_string)
        self._metadata = metadata
        self._pos = 0

    def read(self, size=-1):
        return self._input_string.read(size)

    def get_metadata(self):
        return self._metadata


class FakeStorletFileOut(FakeStorletFile):
    def __init__(self):
        super(FakeStorletFileOut, self).__init__()
        self._output_string = []
        self._metadata = None

    def write(self, data):
        self._output_string.append(data)

    def set_metadata(self, metadata):
        if self._metadata is not None:
            raise IOError('Sending metadata twice is not allowed')
        self._metadata = {}
        # expect the incomming metadata should be dict
        self._metadata.update(metadata)

    def read(self):
        return ''.join(self._output_string)

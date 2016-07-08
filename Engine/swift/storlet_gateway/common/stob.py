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

import copy
import os
import select
from storlet_gateway.common.exceptions import StorletTimeout


class FileDescriptorIterator(object):
    def __init__(self, obj_data, timeout, cancel_func):
        self.closed = False
        self.obj_data = obj_data
        self.timeout = timeout
        self.cancel_func = cancel_func
        self.buf = b''

    def __iter__(self):
        return self

    def read_with_timeout(self, size):
        try:
            with StorletTimeout(self.timeout):
                chunk = os.read(self.obj_data, size)
        except StorletTimeout:
            if self.cancel_func:
                self.cancel_func()
            self.close()
            raise
        except Exception:
            self.close()
            raise
        return chunk

    def next(self, size=64 * 1024):
        if len(self.buf) < size:
            r, w, e = select.select([self.obj_data], [], [], self.timeout)
            if len(r) == 0:
                self.close()

            if self.obj_data in r:
                self.buf += self.read_with_timeout(size - len(self.buf))
                if self.buf == b'':
                    raise StopIteration('Stopped iterator ex')
            else:
                raise StopIteration('Stopped iterator ex')

        if len(self.buf) > size:
            data = self.buf[:size]
            self.buf = self.buf[size:]
        else:
            data = self.buf
            self.buf = b''
        return data

    def _close_check(self):
        if self.closed:
            raise ValueError('I/O operation on closed file')

    def read(self, size=64 * 1024):
        self._close_check()
        return self.next(size)

    def readline(self, size=-1):
        self._close_check()

        # read data into self.buf if there is not enough data
        while b'\n' not in self.buf and \
              (size < 0 or len(self.buf) < size):
            if size < 0:
                chunk = self.read()
            else:
                chunk = self.read(size - len(self.buf))
            if not chunk:
                break
            self.buf += chunk

        # Retrieve one line from buf
        data, sep, rest = self.buf.partition(b'\n')
        data += sep
        self.buf = rest

        # cut out size from retrieved line
        if size >= 0 and len(data) > size:
            self.buf = data[size:] + self.buf
            data = data[:size]

        return data

    def readlines(self, sizehint=-1):
        self._close_check()
        lines = []
        try:
            while True:
                line = self.readline(sizehint)
                if not line:
                    break
                lines.append(line)
                if sizehint >= 0:
                    sizehint -= len(line)
                    if sizehint <= 0:
                        break
        except StopIteration:
            pass
        return lines

    def close(self):
        if self.closed:
            return
        os.close(self.obj_data)
        self.closed = True

    def __del__(self):
        self.close()


class StorletData(object):
    def __init__(self, user_metadata, data_iter=None, data_fd=None,
                 timeout=10, cancel=None):
        if data_iter is None and data_fd is None:
            raise ValueError('Either of data_iter or data_fd should not be '
                             'None')
        if cancel is not None and data_iter is not None:
            raise ValueError('cancel func can only be specified with data_fd')
        self.user_metadata = user_metadata
        self.data_fd = data_fd
        self._data_iter = data_iter
        self.timeout = timeout
        self.cancel = cancel

    @property
    def data_iter(self):
        if self._data_iter is None:
            self._data_iter = FileDescriptorIterator(
                self.data_fd, self.timeout, self.cancel)
        return self._data_iter

    @property
    def has_fd(self):
        return self.data_fd is not None


class StorletRequest(StorletData):
    def __init__(self, storlet_id, params, user_metadata,
                 data_iter=None, data_fd=None, options=None,
                 timeout=10, cancel=None):
        super(StorletRequest, self).__init__(
            user_metadata, data_iter, data_fd, timeout, cancel)
        self.storlet_id = storlet_id
        self.params = copy.deepcopy(params)
        if options is None:
            self.options = {}
        else:
            self.options = options


class StorletResponse(StorletData):
    def __init__(self, user_metadata, data_iter=None, data_fd=None,
                 timeout=10, cancel=None):
        super(StorletResponse, self).__init__(
            user_metadata, data_iter, data_fd, timeout, cancel)

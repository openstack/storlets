# Copyright IBM Corp. 2015, 2015 All Rights Reserved
# Copyright (c) 2010-2016 OpenStack Foundation
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
from contextlib import contextmanager

NOTOPEN = 0
OPEN = 1
CLOSED = 2


class StorletLogger(object):
    def __init__(self, path, name):
        self.full_path = os.path.join(path, '%s.log' % name)
        self._status = NOTOPEN

    def open(self):
        if self._status == OPEN:
            raise Exception('StorletLogger has been open')
        try:
            self._file = open(self.full_path, 'a')
        except Exception:
            raise
        else:
            self._status = OPEN

    def getfd(self):
        if self._status != OPEN:
            # TODO(kota_): Is it safe to return None?
            return None
        return self._file.fileno()

    def getsize(self):
        statinfo = os.stat(self.full_path)
        return statinfo.st_size

    def close(self):
        if self._status != OPEN:
            raise Exception('StorletLogger is not open')
        try:
            self._file.close()
        except Exception:
            raise
        else:
            self._status = CLOSED

    @contextmanager
    def activate(self):
        self.open()
        try:
            yield
        finally:
            self.close()

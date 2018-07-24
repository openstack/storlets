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
import copy
import os
import json


class StorletFile(object):
    mode = 'rb'

    def __init__(self, obj_fd):
        self.obj_fd = obj_fd
        self.obj_file = os.fdopen(obj_fd, self.mode)

    def fileno(self):
        return self.obj_fd

    def seek(self, offset, whence=os.SEEK_SET):
        raise NotImplementedError()

    def read(self, size=-1):
        raise NotImplementedError()

    def readline(self, size=-1):
        raise NotImplementedError()

    def readlines(self, sizehint=-1):
        raise NotImplementedError()

    def write(self, buf):
        raise NotImplementedError()

    def writelines(self, seq):
        raise NotImplementedError()

    def get_metadata(self):
        raise NotImplementedError()

    def set_metadata(self, md):
        raise NotImplementedError()

    def __iter__(self):
        return self

    def next(self):
        buf = self.read()
        if not buf:
            raise StopIteration()
        else:
            return buf

    __next__ = next

    @property
    def closed(self):
        return self.obj_file.closed

    def close(self):
        self.obj_file.close()

    def flush(self):
        raise NotImplementedError()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class StorletOutputFile(StorletFile):
    mode = 'w'

    def __init__(self, md_fd, obj_fd):
        super(StorletOutputFile, self).__init__(obj_fd)
        self._metadata = None
        self.md_file = os.fdopen(md_fd, 'w')

    def get_metadata(self):
        if self._metadata is None:
            raise IOError('Metadata is not set yet')
        return copy.deepcopy(self._metadata)

    def set_metadata(self, md):
        if self.md_file.closed:
            raise IOError('Sending metadata twice is not allowed')
        self.md_file.write(json.dumps(md))
        self._metadata = md
        self.md_file.close()

    def close(self):
        if not self.md_file.closed:
            self.md_file.close()
        super(StorletOutputFile, self).close()

    def write(self, buf):
        if not self.md_file.closed:
            raise IOError('Body should be sent after metadata is sent')
        self.obj_file.write(buf)

    def writelines(self, seq):
        if not self.md_file.closed:
            raise IOError('Body should be sent after metadata is sent')
        self.obj_file.writelines(seq)

    def flush(self):
        self.obj_file.flush()


class StorletInputFile(StorletFile):
    def __init__(self, md, obj_fd):
        super(StorletInputFile, self).__init__(obj_fd)
        self._metadata = md
        self.buf = b''

    def get_metadata(self):
        return copy.deepcopy(self._metadata)

    def _read(self, size=-1):
        return self.obj_file.read(size)

    def read(self, size=-1):
        if size >= 0:
            if len(self.buf) >= size:
                data = self.buf[:size]
                self.buf = self.buf[size:]
            else:
                data = self.buf + self._read(size - len(self.buf))
                self.buf = b''
        else:
            data = self.buf + self._read()
            self.buf = b''
        return data

    def readline(self, size=-1):
        data = b''
        while b'\n' not in data and (size < 0 or len(data) < size):
            if size < 0:
                chunk = self.read(1024)
            else:
                chunk = self.read(size - len(data))
            if not chunk:
                break
            data += chunk
        if b'\n' in data:
            data, sep, rest = data.partition(b'\n')
            data += sep
            self.buf = rest + self.buf
        return data

    def readlines(self, sizehint=-1):
        lines = []
        while True:
            line = self.readline(sizehint)
            if not line:
                break
            lines.append(line)
            if sizehint >= 0:
                sizehint += len(line)
                if sizehint <= 0:
                    break
        return lines


class StorletRangeInputFile(StorletInputFile):
    def __init__(self, md, fd, start, end):
        super(StorletRangeInputFile, self).__init__(md, fd)
        self.start = start
        self.end = end
        # TODO(takashi): Currently we use range input file only for zero copy
        #                case, so can execute seek on fd. Myabe we need some
        #                mechanism to confirm the fd is seekable.
        self.obj_file.seek(self.start, 0)
        self.point = self.start

    def _read(self, size=-1):
        if size >= 0:
            size = min(size, self.end - self.point)
        else:
            size = self.end - self.point

        data = super(StorletRangeInputFile, self)._read(size)
        self.point += len(data)
        return data


class StorletLogger(object):

    def __init__(self, storlet_name, fd):
        self.fd = fd
        self.storlet_name = storlet_name
        self.log_file = os.fdopen(self.fd, 'w')

    @property
    def closed(self):
        return self.log_file.closed

    def close(self):
        self.log_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _emit_log(self, level, msg):
        msg = '%s %s: %s' % (self.storlet_name, level, msg)
        self.log_file.write(msg)

    def debug(self, msg):
        self._emit_log('DEBUG', msg)

    def info(self, msg):
        self._emit_log('INFO', msg)

    def warn(self, msg):
        self._emit_log('WARN', msg)

    warning = warn

    def error(self, msg):
        self._emit_log('ERROR', msg)

    def exception(self, msg):
        raise NotImplementedError()

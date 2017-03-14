/*----------------------------------------------------------------------------
 * Copyright (c) 2010-2016 OpenStack Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * Limitations under the License.
 * ---------------------------------------------------------------------------
 */

package org.openstack.storlet.common;

import java.io.IOException;
import java.io.FileDescriptor;
import java.io.InputStream;
import java.io.FileInputStream;

/**
 * A wrapper class for java.io.FileInputStream
 * that allows access only to a given range within
 * the file.
 * The class overrides the FileInputStream interface
 */
public class RangeFileInputStream extends FileInputStream {

    private final long start;
    private final long end;
    private int available;

    /**
     * Constructs a RangeFileInputStream from a file descriptor and a range
     *
     * @param fd a FileDescriptor instance used to create the
     *           wrapped FileInputStream
     * @param start the beginning of the range.
     * @param end the end of the range
     */
    public RangeFileInputStream(FileDescriptor fd, long start, long end) throws IOException {
            super(fd);
            this.start = start;
            this.end = end;
            this.available = (int)(end - start);
            super.skip(start);
    }

    @Override
    public int available() {
        return this.available;
    }

    @Override
    public int read() throws IOException {
        if (this.available > 0) {
            this.available -= 1;
            return super.read();
        }
        else {
            return -1;
        }
    }

    @Override
    public int read(byte[] b) throws IOException {
        if (available <= 0) {
            return -1;
        }
        int bytesRead = super.read(b, 0, available);
        available -= bytesRead;
        return bytesRead;
    }

    @Override
    public int read(byte[] b, int off, int len) throws IOException {
        if (len == 0) {
            return 0;
        }
        if (available <= 0) {
            return -1;
        }

        int lenToRead;
        if (len > this.available) {
            lenToRead = available;
        } else {
            lenToRead = len;
        }

        int bytesRead = super.read(b,off,lenToRead);
        if (bytesRead > 0) {
            available -= bytesRead;
        } else {
            return -1;
        }
        return bytesRead;
    }

    @Override
    public long skip(long n) throws IOException {
        long toskip;
        if (n > this.available) {
            toskip = this.available;
        } else {
            toskip = n;
        }
        long skipped = super.skip(toskip);
        if (skipped > 0) {
            this.available -= skipped;
        }
        return skipped;
    }

    @Override
    public void mark(int readlimit) {
        return;
    }

    @Override
    public void reset() throws IOException {
        throw new IOException();
    }

    @Override
    public boolean markSupported() {
        return false;
    }
}

/*
 * Copyright (c) 2015, 2016 OpenStack Foundation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.openstack.storlet.common;

import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.IOException;
import java.util.HashMap;

public class StorletInputStream {
    private HashMap<String, String> metadata;
    protected InputStream stream;

    public StorletInputStream(FileDescriptor fd, HashMap<String, String> md) {
        stream = ((InputStream) (new FileInputStream(fd)));
        metadata = md;
    }

    protected StorletInputStream(HashMap<String, String> md) {
        metadata = md;
    }

    public HashMap<String, String> getMetadata() {
        return metadata;
    }

    public InputStream getStream() {
        return stream;
    }

    public void close() {
        try {
            stream.close();
        } catch (IOException e) {
        }
    }
}

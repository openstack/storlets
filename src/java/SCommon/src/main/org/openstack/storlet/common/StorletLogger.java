/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
 * Copyright (c) 2010-2016 OpenStack Foundation
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

import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;

public class StorletLogger {
    private FileOutputStream stream;

    public StorletLogger(FileDescriptor fd) {
        stream = new FileOutputStream(fd);
    }

    public void emitLog(String message) {
        message = message + "\n";
        try {
            stream.write(message.getBytes());
        } catch (IOException e) {

        }

    }

    public void Flush() {
        try {
            stream.flush();
        } catch (IOException e) {
        }
    }

    public void close() {
        Flush();
        try {
            stream.close();
        } catch (IOException e) {
        }
    }
}

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
import java.io.OutputStream;
import java.util.HashMap;

public class StorletOutputStream {
    private HashMap<String, String> metadata;
    protected OutputStream stream;

    public StorletOutputStream(FileDescriptor fd, HashMap<String, String> md) {
        stream = ((OutputStream) (new FileOutputStream(fd)));
        metadata = md;
    }

    public HashMap<String, String> getMetadata() {
        return metadata;
    }

    public void close(){
        try{
            stream.close();
        } catch (IOException e) {
        }
    }
}

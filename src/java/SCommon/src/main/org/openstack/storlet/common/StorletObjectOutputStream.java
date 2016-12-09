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
import java.util.Map;
import java.util.Iterator;

import org.json.simple.JSONObject;

public class StorletObjectOutputStream extends StorletOutputStream {

    private OutputStream MetadataStream_;

    public StorletObjectOutputStream(FileDescriptor data_fd,
            HashMap<String, String> data_md, FileDescriptor md_fd) {
        super(data_fd, data_md);
        MetadataStream_ = ((OutputStream) (new FileOutputStream(md_fd)));
    }

    public OutputStream getStream() {
        return stream;
    }

    public OutputStream getMDStream() {
        return MetadataStream_;
    }

    public void closeMD(){
        try {
            MetadataStream_.close();
        } catch (IOException e) {
        }
    }

    @SuppressWarnings("unchecked")
    public void setMetadata(Map<String, String> md) throws StorletException {
        JSONObject jobj = new JSONObject();
        Iterator<Map.Entry<String, String>> it = md.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<String, String> pairs = (Map.Entry<String, String>) it
                    .next();
            jobj.put((String) pairs.getKey(), (String) pairs.getValue());
            it.remove();
        }
        try {
            MetadataStream_.write(jobj.toString().getBytes());
        } catch (IOException e) {
            throw new StorletException("Failed to set metadata " + e.toString());
        } finally {
            closeMD();
        }
    }
}

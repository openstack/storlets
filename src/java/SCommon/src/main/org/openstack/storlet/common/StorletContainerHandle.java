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
import java.io.IOException;
import java.util.HashMap;
import java.util.Date;

import org.json.simple.JSONObject;

public class StorletContainerHandle extends StorletOutputStream {
    private String containerName;
    private ObjectRequestsTable requestTable;

    public StorletContainerHandle(FileDescriptor request_fd,
            HashMap<String, String> request_md, ObjectRequestsTable requestTable)
            throws StorletException {
        super(request_fd, request_md);
        this.containerName = request_md.get("storlet_container_name");
        if (this.containerName == null)
            throw new StorletException(
                    "StorletContainerHandle init with no container name");
        this.requestTable = requestTable;
    }

    public String getName() {
        return containerName;
    }

    @SuppressWarnings("unchecked")
    public StorletObjectOutputStream getObjectOutputStream(String objectName)
            throws StorletException {
        StorletObjectOutputStream objectStream = null;
        String key = containerName + objectName + new Date().getTime();
        JSONObject jRequestObj = new JSONObject();
        jRequestObj.put("object_name", objectName);
        jRequestObj.put("container_name", containerName);
        jRequestObj.put("key", key);

        ObjectRequestEntry requestEntry = requestTable.Insert(key);

        try {
            stream.write(jRequestObj.toString().getBytes());
        } catch (IOException e) {
            throw new StorletException(
                    "Failed to serialize object descriptor request "
                            + e.toString());
        }

        try {
            objectStream = requestEntry.get();
        } catch (InterruptedException e) {
            throw new StorletException(
                    "Exception while waiting for request entry"
                            + e.getMessage());
        }
        requestTable.Remove(key);
        return objectStream;
    }

    public void close() {
        try {
            stream.close();
        } catch (IOException e) {

        }
    }
}

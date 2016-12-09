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

import java.util.HashMap;

public class ObjectRequestsTable {
    private HashMap<String, ObjectRequestEntry> requestsTable;

    public ObjectRequestsTable() {
        requestsTable = new HashMap<String, ObjectRequestEntry>();
    }

    public ObjectRequestEntry Insert(String key) {
        ObjectRequestEntry requestEntry = new ObjectRequestEntry();
        synchronized (requestsTable) {
            requestsTable.put(key, requestEntry);
        }
        return requestEntry;
    }

    public ObjectRequestEntry Get(String key) {
        return requestsTable.get(key);
    }

    public void Remove(String key) {
        synchronized (requestsTable) {
            requestsTable.remove(key);
        }
    }
}

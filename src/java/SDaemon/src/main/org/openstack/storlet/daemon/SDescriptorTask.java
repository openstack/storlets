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

package org.openstack.storlet.daemon;

import org.slf4j.Logger;
import org.openstack.storlet.common.*;

/*----------------------------------------------------------------------------
 * SDescriptorTask
 * 
 * */
public class SDescriptorTask extends SAbstractTask {
    private ObjectRequestsTable requestsTable_ = null;
    private StorletObjectOutputStream objStream_ = null;
    private String strKey_ = null;

    /*------------------------------------------------------------------------
     * CTOR
     * */
    public SDescriptorTask(StorletObjectOutputStream objStream,
            final String key, ObjectRequestsTable requestsTable, Logger logger) {
        super(logger);
        this.requestsTable_ = requestsTable;
        this.objStream_ = objStream;
        this.strKey_ = key;
    }

    /*------------------------------------------------------------------------
     * run
     * */
    public void run() {
        logger.trace("StorletDescriptorTask: " + "run going to extract key "
                + strKey_);
        ObjectRequestEntry entry = requestsTable_.Get(strKey_);
        logger.trace("StorletDescriptorTask: " + "run got entry "
                + entry.toString());
        try {
            logger.trace("StorletDescriptorTask: "
                    + "run puttting the obj stream in the entry ");
            entry.put(objStream_);
            logger.trace("StorletDescriptorTask: "
                    + "run obj stream is in the table ");
        } catch (InterruptedException e) {
            logger.error("InterruptedException while putting obj stream");
        }
    }
}
/* ============================== END OF FILE =============================== */

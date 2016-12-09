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

import java.io.IOException;
import java.io.OutputStream;

import org.slf4j.Logger;

/*----------------------------------------------------------------------------
 * SCancelTask
 * 
 * Instantiate AbstractTask class. SCancelTask objects contain the task-id,
 * which could later be used to cancel a running storlet (for instance, if
 * a timeout is encountered)
 * */
public class SCancelTask extends SAbstractTask {
    private OutputStream sOut_ = null;
    private String taskId_ = null;

    /*------------------------------------------------------------------------
     * CTOR
     * */
    public SCancelTask(OutputStream sOut, Logger logger, String taskId) {
        super(logger);
        this.sOut_ = sOut;
        this.taskId_ = taskId;
    }

    public String getTaskId() {
        return taskId_;
    }

    public OutputStream getSOut() {
        return sOut_;
    }

    /*------------------------------------------------------------------------
     * run
     * */
    public boolean run() {
        boolean bStatus = true;
        try {
            this.sOut_.write((new String("True: OK")).getBytes());
        } catch (IOException e) {
            e.printStackTrace();
            bStatus = false;
        }
        return bStatus;
    }
}
/* ============================== END OF FILE =============================== */

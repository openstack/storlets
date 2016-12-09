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

package org.openstack.storlet.sbus;

import java.io.FileDescriptor;

/*----------------------------------------------------------------------------
 * SBusRawMessage
 * 
 * This class aggregates the data which is sent through SBus.
 * No logic is implemented here.
 * */

public class SBusRawMessage {
    /*------------------------------------------------------------------------
     * Data Fields
     * */

    // Array of open file descriptors (FDs)
    private FileDescriptor[] hFiles_;

    // JSON-encoded string describing the FDs
    private String strMetadata_;

    // JSON-encoded string with additional information
    // for storlet execution
    private String strParams_;

    /*------------------------------------------------------------------------
     * Default CTOR
     * */
    public SBusRawMessage() {
        hFiles_ = null;
        strMetadata_ = null;
        strParams_ = null;
    }

    /*------------------------------------------------------------------------
     * Setters/getters
     * */
    public FileDescriptor[] getFiles() {
        return hFiles_;
    }

    public void setFiles(FileDescriptor[] hFiles) {
        this.hFiles_ = hFiles;
    }

    public String getMetadata() {
        return strMetadata_;
    }

    public void setMetadata(String strMetadata) {
        this.strMetadata_ = strMetadata;
    }

    public String getParams() {
        return strParams_;
    }

    public void setParams(String strParams) {
        this.strParams_ = strParams;
    }
}
/* ============================== END OF FILE =============================== */

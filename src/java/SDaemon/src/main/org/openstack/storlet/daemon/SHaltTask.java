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
 * SHaltTask
 *
 * Instantiate AbstractTask class. The primary usage intent is to stop
 * a relevant working thread.
 * */
public class SHaltTask extends SAbstractTask {
    private OutputStream sOut_ = null;

    /*------------------------------------------------------------------------
     * CTOR
     * */
    public SHaltTask(OutputStream sOut, Logger logger) {
        super(logger);
        this.sOut_ = sOut;
    }

    /*------------------------------------------------------------------------
     * exec
     *
     * The actual response on "halt" command.
     * */
    @Override
    public boolean exec() {
        respond(this.sOut_, true, new String("OK"));
        return false;
    }
}
/* ============================== END OF FILE =============================== */

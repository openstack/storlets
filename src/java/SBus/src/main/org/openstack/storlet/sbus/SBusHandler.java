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

/*============================================================================
 DD-MMM-2014    eranr     Initial implementation as sChannel.
 Introducing wrapping structures.
 30-Jun-2014    evgenyl   Switching to SBus. Code refactoring.
 Simplifying API. Extracting business logic.
 ===========================================================================*/

package org.openstack.storlet.sbus;

/*----------------------------------------------------------------------------
 * This class encapsulates OS level file descriptor used
 * in Transport Layer APIs.
 * */

public class SBusHandler {
    private int nFD_;

    /*------------------------------------------------------------------------
     * CTOR
     * No default value
     * */
    public SBusHandler(int nFD) {
        nFD_ = nFD;
    }

    /*------------------------------------------------------------------------
     * Getter
     * */
    public int getFD() {
        return nFD_;
    }

    /*------------------------------------------------------------------------
     * Validity
     * */
    public boolean isValid() {
        return (0 <= getFD());
    }

}
/* ============================== END OF FILE =============================== */

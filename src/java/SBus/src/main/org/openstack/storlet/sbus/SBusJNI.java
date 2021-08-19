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

/*----------------------------------------------------------------------------
 * JNI wrapper for low-level C API
 * 
 * Just declarations here.
 * See SBusJNI.c for the implementation
 * */
public class SBusJNI {
    static {
        System.loadLibrary("jsbus");
    }

    public native void startLogger(final String strLogLevel, final String contId);

    public native void stopLogger();

    public native int createSBus(final String strBusName);

    public native int listenSBus(int nBus, float fTimeout);

    public native int sendRawMessage(final String strBusName,
            final SBusRawMessage Msg);

    public native SBusRawMessage receiveRawMessage(int nBus);
}
/* ============================== END OF FILE =============================== */

/*
 * Copyright (c) 2015, 2016 OpenStack Foundation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Designating the host side as the client side and the storlet side
 * as the server side, the IPC between the client and server requires
 * 4 different serialization / de-serialization objects:
 * 1. Serializing client commands (client side)
 * 2. De-srializing client commands (server side)
 * 3. Serializing server response (server side)
 * 4. De-srializing server response (client side)
 * This Java class implements the server side de-serialization objects:
 * ServerSBusOutDatagram
 */
package org.openstack.storlet.sbus;

/*
 * Curerrently we have no Server to Client commands
 * This serves as a place holder should we want to bring the
 * function back:
 * In the past this was used for a allowing a storlet
 * to create new objects via a PUT on container
 * with X-Run-Storlet.
 */
public class ServerSBusOutDatagram {

    public ServerSBusOutDatagram() {
    }

    public SBusRawMessage toRawMessage() {
        return new SBusRawMessage();
    }
}

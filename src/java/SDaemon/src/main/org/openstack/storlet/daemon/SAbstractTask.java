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
package org.openstack.storlet.daemon;

import java.io.IOException;
import java.io.OutputStream;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;

import org.slf4j.Logger;

/*----------------------------------------------------------------------------
 * SAbstractTask
 *
 * A common parent object for different Tasks created by STaskFactory
 * */
public abstract class SAbstractTask {

    protected Logger logger;

    public SAbstractTask(Logger logger) {
        this.logger = logger;
    }

    protected boolean respond(OutputStream ostream, boolean status, String message) {
        JSONObject obj = new JSONObject();
        obj.put("status", status);
        obj.put("message", message);
        boolean bStatus = true;
        try {
            ostream.write(obj.toJSONString().getBytes());
            ostream.flush();
            ostream.close();
        } catch (IOException e) {
            e.printStackTrace();
            bStatus = false;
        }
        return bStatus;
    }

    public abstract boolean exec();
}

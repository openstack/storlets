/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
 * Copyright 2016 OpenStack Foundation
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

package org.openstack.storlet.test;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import org.openstack.storlet.common.IStorlet;
import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletInputStream;
import org.openstack.storlet.common.StorletLogger;
import org.openstack.storlet.common.StorletOutputStream;
import org.openstack.storlet.common.StorletObjectOutputStream;

public class test1 implements IStorlet {
    /***
     * Storlet invoke method.
     * 
     * @throws InterruptedException
     */
    @Override
    public void invoke(ArrayList<StorletInputStream> inputStreams,
            ArrayList<StorletOutputStream> outputStreams,
            Map<String, String> params, StorletLogger logger)
            throws StorletException {
        try {
            logger.emitLog("In test invoke!");
            logger.emitLog("Iterating over params");
            for (Map.Entry<String, String> entry : params.entrySet()) {
                String key = entry.getKey();
                String value = entry.getValue();
                logger.emitLog(key + ":" + value);
            }
            StorletInputStream sins = inputStreams.get(0);
            HashMap<String, String> md = sins.getMetadata();
            StorletObjectOutputStream outStream = (StorletObjectOutputStream) outputStreams
                    .get(0);
            outStream.setMetadata(md);
            OutputStream stream = outStream.getStream();
            logger.emitLog("About to get param op");
            String op = params.get("op");
            if (op == null) {
                logger.emitLog("No op raising...");
                throw new StorletException("no op in params");
            }
            logger.emitLog("Got op " + op);
            if (op.equals("print")) {
                logger.emitLog("op = print");
                String key;
                String value;
                String s;
                for (Map.Entry<String, String> entry : params.entrySet()) {
                    key = entry.getKey();
                    stream.write(key.getBytes());
                    s = "    ";
                    stream.write(s.getBytes());
                    value = entry.getValue();
                    stream.write(value.getBytes());
                    s = "\n";
                    stream.write(s.getBytes());
                }
                stream.close();
                return;
            }

            if (op.equals("crash")) {
                InputStream a = null;
                a.close();
                return;
            }

            if (op.equals("hold")) {
                Thread.sleep(100000);
            }
            outStream.getStream().close();

        } catch (IOException e) {
            logger.emitLog(e.getMessage());
            throw new StorletException(e.getMessage());
        } catch (InterruptedException e) {
            logger.emitLog(e.getMessage());
            throw new StorletException(e.getMessage());
        }
    }
}

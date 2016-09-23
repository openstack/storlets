/*----------------------------------------------------------------------------
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

package org.openstack.storlet.multiinput;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.io.InputStream;
import java.io.OutputStream;

import org.openstack.storlet.common.IStorlet;
import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletInputStream;
import org.openstack.storlet.common.StorletLogger;
import org.openstack.storlet.common.StorletObjectOutputStream;
import org.openstack.storlet.common.StorletContainerHandle;
import org.openstack.storlet.common.StorletOutputStream;
import org.openstack.storlet.common.StorletUtils;

public class MultiInputStorlet implements IStorlet {
    @Override
    public void invoke(ArrayList<StorletInputStream> inputStreams,
            ArrayList<StorletOutputStream> outputStreams,
            Map<String, String> parameters, StorletLogger log)
            throws StorletException {
        log.emitLog("MultiInputStorlet Invoked");

        /*
         * Copy metadata into out md
         */
        HashMap<String, String> md = new HashMap<String, String>();
        for(StorletInputStream psis : inputStreams){
            HashMap<String, String> object_md;
            Iterator it;

            object_md = psis.getMetadata();
            it = object_md.entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry pairs = (Map.Entry) it.next();
                log.emitLog("Putting metadata " + (String) pairs.getKey() + "="
                            + (String) pairs.getValue());
                md.put((String) pairs.getKey(), (String) pairs.getValue());
            }
        }

        /*
         * Execute
         */
        log.emitLog("Let's concat, anyway");

        /*
         * Obtain the storletObjectOutputStream
         */
        StorletObjectOutputStream storletObjectOutputStream;
        storletObjectOutputStream = (StorletObjectOutputStream) outputStreams.get(0);

        /*
         * Now set the output metadata
         */
        log.emitLog("Setting metadata");
        storletObjectOutputStream.setMetadata(md);

        /*
         * Copy data from input stream to output stream
         */
        log.emitLog("Copying data");
        OutputStream os = storletObjectOutputStream.getStream();

        final byte[] buffer = new byte[65536];
        try {
            for(StorletInputStream psis : inputStreams){
                InputStream is;
                is = psis.getStream();

                String readString = null;
                try {
                    log.emitLog("About to read from input");
                    for (int bytes_read = is.read(buffer); bytes_read >= 0; bytes_read = is.read(buffer)) {
                        log.emitLog("read from input " + bytes_read + "bytes");
                        readString = new String(buffer);
                        readString = readString.replaceAll("\0", "");
                        log.emitLog("Writing to output " + bytes_read + "bytes");
                        os.write(readString.getBytes(), 0, bytes_read);
                        log.emitLog("About to read from input");
                    }
                } catch (Exception e) {
                    log.emitLog("Copying data failed: " + e.getMessage());
                } finally {
                    try {
                        psis.close();
                    } catch (Exception e) {
                        log.emitLog("Falied to close input steram " + e.getMessage());
                    }
                }
            }
         } catch(Exception e){
            log.emitLog("Copying data failed in finally: " + e.getMessage());
            throw new StorletException("Copying data failed: " + e.getMessage());
         } finally {
            try {
                os.close();
            } catch (IOException e) {
                log.emitLog("Falied to close input steram " + e.getMessage());
            }
        }
        log.emitLog("MultiInputStorlet Invocation done");
    }
}

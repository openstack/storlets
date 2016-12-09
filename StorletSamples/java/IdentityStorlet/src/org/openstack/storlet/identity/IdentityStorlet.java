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

package org.openstack.storlet.identity;

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

public class IdentityStorlet implements IStorlet {
    @Override
    public void invoke(ArrayList<StorletInputStream> inputStreams,
            ArrayList<StorletOutputStream> outputStreams,
            Map<String, String> parameters, StorletLogger log)
            throws StorletException {
        log.emitLog("IdentityStorlet Invoked");

        /*
         * Copy metadata into out md
         */
        HashMap<String, String> md = new HashMap<String, String>();
        HashMap<String, String> object_md;
        Iterator it;
        StorletInputStream sis = inputStreams.get(0);
        object_md = sis.getMetadata();
        it = object_md.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry pairs = (Map.Entry) it.next();
            log.emitLog("Putting metadata " + (String) pairs.getKey() + "="
                    + (String) pairs.getValue());
            md.put((String) pairs.getKey(), (String) pairs.getValue());
        }

        /*
         * Get optional execute flag
         */
        String strExecute = new String("false");
        if (parameters.get("execute") != null) {
            strExecute = parameters.get("execute");
        }
        boolean bExecute = Boolean.parseBoolean(strExecute);
        int nExitCode = -1;
        /*
         * Execute
         */
        if (bExecute == true) {
            String strJarPath = StorletUtils.getClassFolder(this.getClass());

            // Combine the invocation string
            String strExec = strJarPath + java.io.File.separator + "get42";
            log.emitLog("Exec = " + strExec);
            try {
                // Start process, wait for it to finish, get the exit code
                Process ExecProc = new ProcessBuilder(strExec).start();
                nExitCode = ExecProc.waitFor();
                log.emitLog("Exit code = " + nExitCode);
            } catch (Exception e) {
                log.emitLog("Execution failed. Got Exception " + e.getMessage());
            }
        }

        /*
         * Get optional chunk size
         */
        String strChunkSize = "65536";
        if (parameters.get("chunk_size") != null) {
            strChunkSize = parameters.get("chunk_size");
        }
        int iChunkSize;
        try {
            iChunkSize = Integer.parseInt(strChunkSize);
        } catch (NumberFormatException e) {
            log.emitLog("The chunk_size parameter is not an integer");
            throw new StorletException(
                    "The chunk_size parameter is not an integer");
        }

        /*
         * 1) If the output stream is StorletObjectOutputStream we are in a GET
         * or PUT scenario where we copy the data and metadata into it. 2) If
         * the output stream is StorletContainerHandle we are in a Storlet batch
         * scenario where we first ask for a StorletObjectOutputStream, and then
         * do the copy.
         */
        StorletObjectOutputStream storletObjectOutputStream;
        StorletOutputStream storletOutputStream = outputStreams.get(0);
        if (storletOutputStream instanceof StorletContainerHandle) {
            log.emitLog("Requesting for output object");
            StorletContainerHandle storletContainerHandle = (StorletContainerHandle) storletOutputStream;
            String objectName = new String(storletContainerHandle.getName()
                    + "/copy_target");
            storletObjectOutputStream = storletContainerHandle
                    .getObjectOutputStream(objectName);
            storletContainerHandle.close();
        } else {
            storletObjectOutputStream = (StorletObjectOutputStream) outputStreams
                    .get(0);
        }

        /*
         * add execution invocation result to out md
         */
        if (bExecute == true) {
            md.put("Execution result", Integer.toString(nExitCode));
        }
        /*
         * Copy parameters into out md
         */
        it = parameters.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry pairs = (Map.Entry) it.next();
            log.emitLog("Putting parameter " + (String) pairs.getKey() + "="
                    + (String) pairs.getValue());
            md.put("Parameter-" + (String) pairs.getKey(),
                    (String) pairs.getValue());
        }

        /*
         * Now set the output metadata
         */
        log.emitLog("Setting metadata");
        storletObjectOutputStream.setMetadata(md);

        /*
         * Get optional double flag
         */
        String strDouble = new String("false");
        if (parameters.get("double") != null) {
            strDouble = parameters.get("double");
        }
        boolean bDouble = Boolean.parseBoolean(strDouble);
        log.emitLog("bDouble is " + bDouble);

        /*
         * Copy data from input stream to output stream
         */
        log.emitLog("Copying data");
        StorletInputStream psis = (StorletInputStream) inputStreams.get(0);
        InputStream is;
        is = psis.getStream();

        OutputStream os = storletObjectOutputStream.getStream();
        final byte[] buffer = new byte[iChunkSize];
        String readString = null;
        try {
            log.emitLog(new Date().toString() + "About to read from input");
            for (int bytes_read = is.read(buffer); bytes_read >= 0; bytes_read = is
                    .read(buffer)) {
                log.emitLog(new Date().toString() + "read from input "
                        + bytes_read + "bytes");
                readString = new String(buffer);
                readString = readString.replaceAll("\0", "");
                log.emitLog(new Date().toString() + "Writing to output "
                        + bytes_read + "bytes");
                os.write(readString.getBytes(), 0, bytes_read);
                if (bDouble == true) {
                    log.emitLog("bDouble == true writing again");
                    log.emitLog(new Date().toString() + "Writing to output "
                            + bytes_read + "bytes");
                    // os.write(buffer);
                    os.write(readString.getBytes());
                }
                log.emitLog("About to read from input");
            }
            os.close();
        } catch (Exception e) {
            log.emitLog("Copying data from inut stream to output stream failed: "
                    + e.getMessage());
            throw new StorletException(
                    "Copying data from inut stream to output stream failed: "
                            + e.getMessage());
        } finally {
            try {
                is.close();
                os.close();
            } catch (IOException e) {
            }
        }
        log.emitLog("IdentityStorlet Invocation done");
    }
}

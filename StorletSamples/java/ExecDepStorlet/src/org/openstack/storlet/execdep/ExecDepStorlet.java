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

package org.openstack.storlet.execdep;

import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.Map.Entry;

import org.openstack.storlet.common.IStorlet;
import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletInputStream;
import org.openstack.storlet.common.StorletLogger;
import org.openstack.storlet.common.StorletObjectOutputStream;
import org.openstack.storlet.common.StorletOutputStream;
import org.openstack.storlet.common.StorletUtils;

/*----------------------------------------------------------------------------
 * ExecDepStorlet
 * 
 * This class invokes another executable.
 * The idea is to check that the dependencies are set up correctly, i.e.
 * copied and "chmod"-ed.
 * */
public class ExecDepStorlet implements IStorlet {
    private final int nExpectedReturnCode_ = 42;

    @Override
    public void invoke(ArrayList<StorletInputStream> inputStreams,
            ArrayList<StorletOutputStream> outputStreams,
            Map<String, String> arg2, StorletLogger log)
            throws StorletException {
        StorletInputStream sinob = null;
        StorletObjectOutputStream sout = null;
        try {
            String strContent = "...:::== Inside ExecDepStorlet ==:::...";
            String strTimeStamp = new SimpleDateFormat("dd-MM-yyy HH:mm:ss")
                    .format(new Date());
            log.emitLog(strContent);
            log.emitLog(strTimeStamp);

            sinob = inputStreams.get(0);
            HashMap<String, String> md = sinob.getMetadata();
            sout = (StorletObjectOutputStream) outputStreams.get(0);
            Iterator<Entry<String, String>> ii = md.entrySet().iterator();
            while (ii.hasNext()) {
                @SuppressWarnings("rawtypes")
                Map.Entry kv = (Map.Entry) ii.next();
                log.emitLog("[ " + kv.getKey() + " ] = " + kv.getValue());
            }
            // Get the source location of this class image
            String strJarPath = StorletUtils.getClassFolder(this.getClass());

            // Combine the invocation string
            String strExec = strJarPath + java.io.File.separator + "get42";
            log.emitLog("Exec = " + strExec);
            // Start process, wait for it to finish, get the exit code
            Process ExecProc = new ProcessBuilder(strExec).start();
            int nExitCode = ExecProc.waitFor();
            String strInvRes = "Exit code = " + nExitCode;
            md.put("depend-ret-code", "" + nExitCode);
            sout.setMetadata(md);
            log.emitLog(strInvRes);
        } catch (Exception e) {
            System.err.print("Exception: " + e.getMessage());
            log.emitLog("Exception: " + e.getMessage());
            throw new StorletException(e.getMessage());
        } finally {
            try {
                if (sinob != null)
                    sinob.getStream().close();
                if (sout != null) {
                    sout.getStream().close();
                    sout.getMDStream().close();
                }

            } catch (IOException e) {
            }
        }
    }
}

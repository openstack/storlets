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

package org.openstack.storlet;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.io.OutputStream;

import org.openstack.storlet.common.IStorlet;
import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletInputStream;
import org.openstack.storlet.common.StorletLogger;
import org.openstack.storlet.common.StorletObjectOutputStream;
import org.openstack.storlet.common.StorletContainerHandle;
import org.openstack.storlet.common.StorletOutputStream;
import org.openstack.storlet.common.StorletUtils;

/***
 * An identity storlet for record based text files.
 * Records are separated with a newline delimiter.
 * The storlet is used for testing range requests
 * where ranges can cross records boundaries.
 * In order not to lose any record split between ranges
 * we do the following:
 * Given a range [start, end] the actual range being sent to
 * the storlet is going to be [start, end + max_record_line]
 * where the max record line is the maximum length of a record
 * Note that this range is calculated outside of the storlet
 * however, the storlet needs to be aware that the range it got
 * is of the form [start,end + max_record_line]
 * In addition pass the storlet a boolean 'firstPartition' telling
 * whether this is the first range of the file or not
 * With this the storlet proceeds as follows:
 * (1) If firstPartition is True, the storlet begins at 'start' and
 *     processes records until it gets to 'end'. Once getting to
 *     the 'end' position the storlet proceeds until it reaches a
 *     record termination. This means that if the end position was
 *     at the middle of a record, the whole record is processed. If,
 *     however, the end position was exactly at the end of a record,
 *     the storlet processed on more complete record
 * (2) If firstPartition is False, the storlet skips the data until
 *     it reaches a record termination, and starts processing as
 *     described in (1)
 */
public class PartitionsIdentityStorlet implements IStorlet {
    long m_start, m_end, m_length;
    int m_max_record_line;
    boolean m_firstPartition;
    BufferedReader m_br = null;

        long m_total_lines_emitted = 0;

    StorletLogger m_log;

    private void safeClose(OutputStream os, InputStream is) {
        try {
            if (m_br != null) m_br.close();
        } catch (IOException e) {
        }
        try {
            if (os != null) os.close();
        } catch (IOException e) {
        }
        try {
            if (is != null) os.close();
        } catch (IOException e) {
        }
    }

    private void parseInputParameters(Map<String, String> parameters) throws Exception {
        if (parameters.get("start") != null) {
            m_start = Long.parseLong(parameters.get("start"));
        } else {
            m_log.emitLog("Missing mandatory start parameter");
            throw new Exception("Missing mandatory start parameter");
        }
        if (parameters.get("end") != null) {
            m_end = Long.parseLong(parameters.get("end"));
        } else {
            m_log.emitLog("Missing mandatory end parameter");
            throw new Exception("Missing mandatory end parameter");
        }
        if (parameters.get("max_record_line") != null) {
            m_max_record_line = Integer.parseInt(parameters.get("max_record_line"));
        } else {
            m_log.emitLog("Missing mandatory max_record_line parameter");
            throw new Exception("Missing mandatory max_record_line parameter");
        }
        if (parameters.get("first_partition") != null) {
            m_firstPartition = Boolean.parseBoolean(parameters.get("first_partition"));
        } else {
            m_log.emitLog("Missing mandatory first_partition parameter");
            throw new Exception("Missing mandatory first_partition parameter");
        }
        m_length = m_end - m_start;
    }

    private int consumeFirstLine(OutputStream os) throws IOException {
        String line;
        line = m_br.readLine();
        if (line == null) {
            m_log.emitLog("m_br fully consumed on first line");
            throw new IOException("m_br fully consumed on first line");
        }
        if (m_firstPartition == true) {
                        m_total_lines_emitted += 1;
            //m_log.emitLog("This is the first partition, writing first line");
            //m_log.emitLog("wrote: " + new String(line.getBytes(),"UTF-8") + "\n");
            os.write(line.getBytes());
                    os.write('\n');
        } else {
            //m_log.emitLog("This is NOT the first partition, skipping first line");
        }

        return line.length() + 1;
    }

    @Override
    public void invoke(ArrayList<StorletInputStream> inputStreams,
            ArrayList<StorletOutputStream> outputStreams,
            Map<String, String> parameters, StorletLogger log)
            throws StorletException {
        m_log = log;
        m_log.emitLog("PartitionsIdentityStorlet Invoked");

                StorletObjectOutputStream sos = null;
                OutputStream os = null;
                InputStream is = null;
                try {
            sos = (StorletObjectOutputStream)outputStreams.get(0);
            sos.setMetadata(new HashMap<String, String>());
            os = sos.getStream();
            is = inputStreams.get(0).getStream();
        } catch (Exception ex) {
                m_log.emitLog("Failed to get streams from Storlet invoke inputs");
            safeClose(os, is);
                        return;
        }

        /*
         * Get mandatory parameters
         */
        try {
            parseInputParameters(parameters);
        } catch (Exception ex) {
                m_log.emitLog("Failed to initialize input stream");
            safeClose(os, is);
                        return;
        }

        String line;
        int lineLength = 0;
        try {
            m_br = new BufferedReader(new InputStreamReader(is));
        } catch (Exception ex) {
                m_log.emitLog("Failed to initialize input stream");
                        safeClose(os, is);
                        return;
                }

                try {
            lineLength = consumeFirstLine(os);
        } catch (Exception ex) {
                m_log.emitLog("Failed to consume first line");
                        safeClose(os, is);
                        return;
                }

        m_length -= lineLength;
        try {
            // We allow m_length to get to -1 so as to read an extra record
            // if m_end points exactly to an end of a record.
            while ( ((line = m_br.readLine()) != null) && (m_length >= -1) ) {
                                m_total_lines_emitted += 1;
                os.write(line.getBytes());
                os.write('\n');
                //m_log.emitLog("m_length is " + m_length);
                //m_log.emitLog("wrote: " + new String(line.getBytes(),"UTF-8") + "\n");
                m_length -= (line.length() + 1);
            }
                        if (m_length > 0)
                m_log.emitLog("Got a null line while not consuming all range");

        } catch (Exception ex) {
            m_log.emitLog("Exception while consuming range " + Arrays.toString(ex.getStackTrace()) );
        } finally {
                        safeClose(os, is);
        }
                m_log.emitLog("Total lines emitted: " + m_total_lines_emitted);
    }
}

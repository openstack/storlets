/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
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

package com.ibm.storlet.testmetadatastorlet;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.io.InputStream;
import java.io.OutputStream;

import com.ibm.storlet.common.IStorlet;
import com.ibm.storlet.common.StorletException;
import com.ibm.storlet.common.StorletInputStream;
import com.ibm.storlet.common.StorletLogger;
import com.ibm.storlet.common.StorletObjectOutputStream;
import com.ibm.storlet.common.StorletOutputStream;

public class MetadataStorlet implements IStorlet 
{
    @Override
    public void invoke( ArrayList<StorletInputStream>  inputStreams,
                        ArrayList<StorletOutputStream> outputStreams, 
                        Map<String, String>            parameters,
                        StorletLogger                  log ) 
                                                       throws StorletException {
    	log.emitLog("Test Metadata Storlet Invoked");
    	final InputStream inputStream = inputStreams.get(0).getStream();
        final HashMap<String, String> metadata = inputStreams.get(0).getMetadata();
        final StorletObjectOutputStream storletObjectOutputStream = (StorletObjectOutputStream) outputStreams.get(0);
		Iterator it = metadata.entrySet().iterator();
		log.emitLog("Printing the input metadata");
	    while (it.hasNext()) {
	        Map.Entry pairs = (Map.Entry)it.next();
	        log.emitLog((String)pairs.getKey() + " : "+ (String)pairs.getValue());
	    }
        
        metadata.put("override_key", "new_value");
        it = metadata.entrySet().iterator();
		log.emitLog("Printing the input metadata");
	    while (it.hasNext()) {
	        Map.Entry pairs = (Map.Entry)it.next();
	        log.emitLog((String)pairs.getKey() + " : "+ (String)pairs.getValue());
	    }
        storletObjectOutputStream.setMetadata(metadata);
                
        OutputStream outputStream = storletObjectOutputStream.getStream();
        try {
            byte[] bytearray = new byte[100];
            inputStream.read(bytearray ,0,100);

        	outputStream.write("1234567890".getBytes());
        	inputStream.close();
        	outputStream.close();
        } catch (IOException ex) {
            log.emitLog(ex.getMessage());
            throw new StorletException(ex.getMessage());
        }   
	 }
}

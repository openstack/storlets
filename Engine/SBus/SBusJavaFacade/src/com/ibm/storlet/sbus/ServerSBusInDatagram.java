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
 * This Java class implements the server side serialization objects:
 * ServerSBusInDatagram
 */
package com.ibm.storlet.sbus;

import java.io.FileDescriptor;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import org.json.simple.JSONObject;
import org.json.simple.JSONArray;

public class ServerSBusInDatagram {

	private int numFDs;
	private FileDescriptor[] fds;
	private String command;
	private HashMap<String, String> params;
	private HashMap<String, String>[] metadata;
	private String taskID;

	/**
	 * Parses a raw message coming from the wire.
	 * The incoming message is constructed by the ClientSBusOutDatagram.
	 * The message is structured as follows:
	 * Array of file descriptors, already parsed in SBusRawMessage
	 * A command related json string of the following structure:
	 * {
	 *     "command": "command encoded as string",
	 *     "params": {                            // This element is optional
	 *         "key1": "value1",
	 *         ...
	 *     },
	 *     "task_id": "task id encoded as string" // This element is optional
	 * }
	 * File descriptors metadata, encoded as a JSON array with one
	 * element per file descriptor. The i'th element in the array
	 * consists of the metadata of the i'th element in the file
	 * descriptors array:
	 * [
	 *     {
	 *         "type": "the fd type encoded as string",  // Mandatory
	 *         "metadata key1": "metadata value 1",
	 *         ...
	 *     },
	 *     ...
	 * ]
	 * All the values in the above JSON elemens are strings.
	 * Once constructed the class provides all necessary accessors to the parsed
	 * fields.
	 * @param msg	the raw mwssage consisting of the string encoded json formats
	 * @see SBusPythonFacade.ClientSBusOutDatagram the python code that serilializes the datagram
	 * @see SBusPythonFacade.ServerSBusInDatagram the equivalent python code
	 */
	public ServerSBusInDatagram(final SBusRawMessage msg) throws ParseException {
		this.fds = msg.getFiles();
                numFDs = this.fds == null ? 0 : this.fds.length;

		JSONObject jsonCmdParams = (JSONObject)(new JSONParser().parse(msg.getParams()));
		this.command = (String)jsonCmdParams.get("command");
		this.params = new HashMap<String, String>();
		if (jsonCmdParams.containsKey("params")) {
			JSONObject jsonParams = (JSONObject)jsonCmdParams.get("params");
			for (Object key : jsonParams.keySet()) {
				this.params.put((String)key, (String)jsonParams.get(key));
			}
		}
		if (jsonCmdParams.containsKey("task_id")) {
			this.taskID = (String)jsonCmdParams.get("task_id");
		}

		String strMD = msg.getMetadata();
                this.metadata = (HashMap<String, String>[]) new HashMap[getNFiles()];
		JSONArray jsonarray = (JSONArray)(new JSONParser().parse(strMD));
		Iterator it = jsonarray.iterator();
		int i=0;
		while (it.hasNext()) {
			JSONObject jsonobject = (JSONObject)it.next();
			this.metadata[i] = new HashMap<String, String>();
			for (Object key : jsonobject.keySet()) {
				String strKey = (String)key;
				String strVal = (String)jsonobject.get(key);
				this.metadata[i].put(strKey, strVal);
			}
			i++;
		}
	}

	public FileDescriptor[] getFiles() {
                return fds;
        }

        public int getNFiles() {
                return numFDs;
        }

        public String getCommand() {
                return command;
        }

        public HashMap<String, String> getExecParams() {
                return params;
        }

	public String getTaskId() {
		return taskID;
	}

	public HashMap<String, String>[] getFilesMetadata() {
		return metadata;
	}
}

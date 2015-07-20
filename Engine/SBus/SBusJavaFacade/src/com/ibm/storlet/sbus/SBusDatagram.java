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

/*============================================================================
 07-Jul-2014    evgenyl     Initial implementation.
 17-Jul-2014    evgenyl     Covering different enumerator representations
                            in Java and Python JSON marshaling
 09-Oct-2014	eranr		Calling setExecParams( JustParams ) even if
 							JustParams is empty. Otherwise, upper layer
 							may crash if there were no parameters.
 ===========================================================================*/

package com.ibm.storlet.sbus;

import java.io.FileDescriptor;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.json.simple.JSONObject;
import org.json.simple.parser.ContainerFactory;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

/*----------------------------------------------------------------------------
 * SBusDatagram
 * 
 * This class aggregates the data which is sent through SBusBackend. 
 * The data is collected and encoded as a SBusRawMessage
 * */

public class SBusDatagram 
{
	/*------------------------------------------------------------------------
	 * Enumerating commands
	 * 
	 * The list should be synchronized with its Python counterpart
	 * */
	public static enum eStorletCommand
	{
		SBUS_CMD_HALT           (0),
		SBUS_CMD_EXECUTE        (1),
		SBUS_CMD_START_DAEMON   (2),
		SBUS_CMD_STOP_DAEMON    (3),
		SBUS_CMD_DAEMON_STATUS  (4),
		SBUS_CMD_STOP_DAEMONS   (5),
		SBUS_CMD_PING           (6),
		SBUS_CMD_DESCRIPTOR     (7),
		SBUS_CMD_CANCEL         (8),
		SBUS_CMD_NOP            (9);
				
		private eStorletCommand(int n){}
	};
	
	
	/*------------------------------------------------------------------------
	 * Enumerating file usage intents
	 * 
	 * The list should be synchronized with its Python counterpart
	 * */
	public static enum eFileDescription
	{
		SBUS_FD_INPUT_OBJECT                (0),
		SBUS_FD_OUTPUT_OBJECT               (1),
		SBUS_FD_OUTPUT_OBJECT_METADATA      (2),
		SBUS_FD_OUTPUT_OBJECT_AND_METADATA  (3),
		SBUS_FD_LOGGER                      (4),
		SBUS_FD_OUTPUT_CONTAINER            (5),
		SBUS_FD_OUTPUT_TASK_ID              (6);

		private eFileDescription(int n){}
	};	
	
	// Array of open file descriptors (FDs)
	private FileDescriptor[] hFiles_;
	// Number of open file descriptors
	private int nFiles_;
	// Command to execute
	private eStorletCommand eCommand_;
	// identifier for the task
        private static String taskId_; 
	// Metadata for the file descriptors
	// Descriptor usage intents - input, output, etc
    private HashMap<String, String>[] FilesMetadata_;
    // Additional execution parameters for the storlet
    private HashMap<String, String> ExecParams_;
    
    // The key name to store eCommand_ field in ExecParams_ hash
    // during data transfer. 
    private final static String strCommandKeyName = "command"; 
    private final static String strTaskIdName = "taskId"; 
	/*------------------------------------------------------------------------
	 * Default CTOR
	 * */    
    public SBusDatagram()
    {
    	this.hFiles_ 		= null;
    	this.nFiles_ 		= 0;
    	this.eCommand_ 		= eStorletCommand.SBUS_CMD_NOP;
    	this.FilesMetadata_	= null;
    	this.ExecParams_ 	= null;
    	this.taskId_            = null;
    }

	/*------------------------------------------------------------------------
	 * Conversion CTOR
	 * */    
    public SBusDatagram( final SBusRawMessage RawMsg )
    {
    	setFiles( RawMsg.getFiles() );
    	setCommandAndParamsFromJSON( RawMsg.getParams() );
    	setFilesMetadataFromJSON( RawMsg.getMetadata() );	    
    }
    
    /*------------------------------------------------------------------------
     * setCommandAndParamsFromJSON
     * 
     * Assumption: command field is in the map encoded in the JSON string  
     * */    
    private void setCommandAndParamsFromJSON( String strJSONParams )
    {
    	HashMap<String, ?> ParamsAndCommand = 
    	                                    convertJSONtoMap( strJSONParams );
    	HashMap<String, String> JustParams = new HashMap<String, String>();
    	for( Entry<String, ?> e : ParamsAndCommand.entrySet() )
    	{
    	    String strKey   = e.getKey();
    	    String strValue = e.getValue().toString();
    	    if( strKey.equals(strCommandKeyName) )
    	        setCommand( convertStringToCommand( strValue ) );
    	    else if ( strKey.equals(strTaskIdName) )
                setTaskId( strValue );
            else
    	        JustParams.put( strKey, strValue );
    	}
    	
    	setExecParams( JustParams );
    }
    
    /*------------------------------------------------------------------------
     * setFilesMetadataFromJSON
     * */    
    private void setFilesMetadataFromJSON( String strJSONMetadata )
    {
        // There are no files. So, no metadata to store.
        // strJSONMetadata holds an empty map
        if( 0 == getNFiles() )
            return;
        
        @SuppressWarnings("unchecked")
        HashMap<String, String>[] FilesMetadata = 
                (HashMap<String, String>[]) new HashMap[getNFiles()];
        
        HashMap<String, String> HashOfHashes = 
                                          convertJSONtoMap( strJSONMetadata );
        for( int i = 0; i < getNFiles(); ++i )
        {
            String strIdx = new String() + i;
            String strCurrJSONMetadata = HashOfHashes.get( strIdx );
            HashMap<String, ?> ObtainedMetadata = 
                                       convertJSONtoMap(strCurrJSONMetadata );
            FilesMetadata[i] = prepareMetadata(ObtainedMetadata);
        }
        setFilesMetadata( FilesMetadata );
    }
    
    /*------------------------------------------------------------------------
     * prepareMetadata
     * 
     * Auxiliary method for JSON parsing
     * */    
    private HashMap<String, String> prepareMetadata( HashMap<String,?> Orig )
    {
        HashMap<String, String> Result = new HashMap<String, String>();
        String value;
        for( Entry<String, ?> e : Orig.entrySet() ) {
        	if (e.getKey().toString().equals("type")) {
        		value = convertFileTypeToString( e.getValue().toString() );
        	} else {
        		value = e.getValue().toString();
        	}
            Result.put( e.getKey().toString(), value);
        }
        return Result;
    }

    /*------------------------------------------------------------------------
     * convertJSONtoMap
     * 
     * Auxiliary method for JSON parsing
     * */    
    private HashMap<String, String> convertJSONtoMap( String strJSON )
    {
        HashMap<String, String> Res = null;
        try 
        {
            @SuppressWarnings("unchecked")
            HashMap<String, String>  r = ( HashMap<String, String>) 
                    new JSONParser().parse(strJSON, new ContainerFactory()
                    {
                        // Inner class for parsing only.
                        @SuppressWarnings("rawtypes")
                        public Map createObjectContainer()
                        {
                            return new HashMap<String, String>();
                        }
                        
                        @SuppressWarnings("rawtypes")
                        public List creatArrayContainer()
                        {
                            return new ArrayList();
                        }
                    } );
            Res = r;
        } 
        catch (ParseException e) 
        {
            e.printStackTrace();
        }
        return Res;
    }
    
	/*------------------------------------------------------------------------
	 * toRawMessage
	 * 
	 * Converter to Raw Message format
	 * */    
    public SBusRawMessage toRawMessage()
    {
    	SBusRawMessage Res = new SBusRawMessage();
    	Res.setFiles(    this.getFiles()                  );
	    Res.setParams(   this.getParamsAndCommandAsJSON() );
	    Res.setMetadata( this.getFilesMetadataAsJSON()    );	    
	    return Res;
    }
    
    /*------------------------------------------------------------------------
     * getParamsAndCommandAsJSON
     * 
     * Take ExecParams_, put a pair "command"=eCommand_ inside,
     * encode as a JSON string 
     * */    
    private String getParamsAndCommandAsJSON()
    {
    	HashMap<String, String> Params = null;
    	if( null == getExecParams() || getExecParams().isEmpty() )
    	    Params = new HashMap<String, String>();
    	else
    		Params = new HashMap<String, String>( getExecParams() );
    	Params.put( strCommandKeyName, getCommand().toString() );
    	Params.put( strTaskIdName, getTaskId() );
    	return JSONObject.toJSONString( Params );   	
    }
    
    /*------------------------------------------------------------------------
     * getFilesMetadataAsJSON
     * 
     * Iterate through meta-data HashMaps array and create a new HashMap
     * by the following rule - 
     * Key: Take the sequential index of the suitable FileDescriptor,
     *      make a string of it.
     * Value: Take the suitable HashMap, encode it as a JSON string.
     * 
     *  Take the combined HashMap, encode it as a JSON string
     * */    
    private String getFilesMetadataAsJSON()
    {
    	HashMap<String, String> CombMetadata = new HashMap<String, String>();
    	for( int i = 0; i < getNFiles(); ++i )
    	{
            HashMap<String, String> CurrFileMD = getFilesMetadata()[i];
            String strCurrFileMD = JSONObject.toJSONString( CurrFileMD ); 
            String strHashID = new String() + i;
            CombMetadata.put( strHashID, strCurrFileMD );
    	}
    	return JSONObject.toJSONString( CombMetadata ); 
    }

    /*------------------------------------------------------------------------
     * convertStringToCommand
     * */
    private eStorletCommand convertStringToCommand( final String strVal )
    {
        eStorletCommand eCmd = eStorletCommand.SBUS_CMD_NOP;

        if(     strVal.equals("0") || strVal.equals("SBUS_CMD_HALT"))
            eCmd = eStorletCommand.SBUS_CMD_HALT;
        else if(strVal.equals("1") || strVal.equals( "SBUS_CMD_EXECUTE" ))
            eCmd = eStorletCommand.SBUS_CMD_EXECUTE;
        else if(strVal.equals("2") || strVal.equals( "SBUS_CMD_START_DAEMON"))
            eCmd = eStorletCommand.SBUS_CMD_START_DAEMON;
        else if(strVal.equals("3") || strVal.equals( "SBUS_CMD_STOP_DAEMON" ))
            eCmd = eStorletCommand.SBUS_CMD_STOP_DAEMON;
        else if(strVal.equals("4") || strVal.equals("SBUS_CMD_DAEMON_STATUS"))
            eCmd = eStorletCommand.SBUS_CMD_DAEMON_STATUS;
        else if(strVal.equals("5") || strVal.equals( "SBUS_CMD_STOP_DAEMONS"))
            eCmd = eStorletCommand.SBUS_CMD_STOP_DAEMONS;
        else if(strVal.equals("6") || strVal.equals( "SBUS_CMD_PING" ))
            eCmd = eStorletCommand.SBUS_CMD_PING;
        else if(strVal.equals("7") || strVal.equals( "SBUS_CMD_DESCRIPTOR" ))
            eCmd = eStorletCommand.SBUS_CMD_DESCRIPTOR;
        else if(strVal.equals("8") || strVal.equals( "SBUS_CMD_CANCEL" ))
            eCmd = eStorletCommand.SBUS_CMD_CANCEL;
       
        return eCmd;
    }

    /*------------------------------------------------------------------------
     * convertFileTypeToString
     * */
    private String convertFileTypeToString( final String strFileType )
    {
        String strType = new String( strFileType ); 
        switch(strFileType)
        {
        case "0":
            strType = "SBUS_FD_INPUT_OBJECT";
            break;
        case "1":
            strType = "SBUS_FD_OUTPUT_OBJECT";
            break;
        case "2":
            strType = "SBUS_FD_OUTPUT_OBJECT_METADATA";
            break;
        case "3":
            strType = "SBUS_FD_OUTPUT_OBJECT_AND_METADATA";
            break;
        case "4":
            strType = "SBUS_FD_LOGGER";
            break;
        case "5":
            strType = "SBUS_FD_OUTPUT_CONTAINER";
            break;
        case "6":
            strType = "SBUS_FD_OUTPUT_TASK_ID";
            break;
        }
        return strType;
    }
    
    /*------------------------------------------------------------------------
	 * Setters/getters
	 * */    
	public FileDescriptor[] getFiles() 
	{
		return hFiles_;
	}
	public void setFiles(FileDescriptor[] hFiles) 
	{
		this.hFiles_ = hFiles;
		this.nFiles_ = null == hFiles ? 0 : hFiles.length;
	}
	public int getNFiles()
	{
		return nFiles_;
	}
        public eStorletCommand getCommand()
        {
                return eCommand_;
        }
        public void setCommand(eStorletCommand eCommand)
        {
                this.eCommand_ = eCommand;
        }
	public String getTaskId() 
	{
		return taskId_;
	}
	public void setTaskId(String id)
	{
		this.taskId_ = id;
	}
	public HashMap<String, String>[] getFilesMetadata() 
	{
		return FilesMetadata_;
	}
	public void setFilesMetadata(HashMap<String, String>[] filesMetadata) 
	{
		FilesMetadata_ = filesMetadata;
	}
	public HashMap<String, String> getExecParams() 
	{
		return ExecParams_;
	}
	public void setExecParams(HashMap<String, String> execParams) 
	{
		ExecParams_ = execParams;
	}
}
/*============================== END OF FILE ===============================*/

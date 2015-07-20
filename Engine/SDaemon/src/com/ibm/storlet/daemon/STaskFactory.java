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
 DD-MMM-YYYY    eranr       Initial implementation.
 10-Jul-2014    evgenyl     Refactoring. Switching to SBusDatagram.
 01-Oct-2014    evgenyl     Drop "type" from INPUT_STREAM metadata
 ===========================================================================*/
package com.ibm.storlet.daemon;

import java.io.FileOutputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;

import org.slf4j.Logger;

import com.ibm.storlet.common.*;
import com.ibm.storlet.daemon.SExecutionTask;
import com.ibm.storlet.sbus.SBusDatagram;
import com.ibm.storlet.sbus.SBusDatagram.eStorletCommand;

/*----------------------------------------------------------------------------
 * StorletTaskFactory
 * 
 * Analyze the request datagram. Setup the obtained file descriptors.
 * Prepare the storlet execution environment
 * */
public class STaskFactory 
{
	private IStorlet storlet_;
	private Logger logger_;
	private ObjectRequestsTable requestsTable_; 
	
	/*------------------------------------------------------------------------
	 * CTOR
	 * */
	public STaskFactory( IStorlet storlet, Logger logger )
	{
		this.storlet_         = storlet;
		this.logger_          = logger;
		this.requestsTable_   = new ObjectRequestsTable();
	}
	
	/*------------------------------------------------------------------------
	 * createStorletTask
	 * 
	 * Factory entry point
	 * */
	public SAbstractTask createStorletTask( SBusDatagram dtg ) 
	                                                   throws StorletException
    {
	    SAbstractTask ResObj = null;
		eStorletCommand command = dtg.getCommand();
		
		if( eStorletCommand.SBUS_CMD_HALT == command ) 
		{
			this.logger_.trace( "createStorletTask: " +
		                        "received HALT command");
			ResObj = new SHaltTask( logger_ );
		} 
		else if( eStorletCommand.SBUS_CMD_EXECUTE == command ) 
		{
			this.logger_.trace( "createStorletTask: " + 
		                        "received EXECUTE command");
			ResObj = createExecutionTask( dtg );
		} 
        else if( eStorletCommand.SBUS_CMD_DESCRIPTOR == command ) 
        {
            this.logger_.trace( "createStorletTask: " +
                                "received Descriptor command");
            ResObj = createDescriptorTask( dtg );
        }
        else if( eStorletCommand.SBUS_CMD_PING == command ) 
        {
            this.logger_.trace( "createStorletTask: " +
                                "received Ping command");
            ResObj = createPingTask( dtg );
        }
        else if( eStorletCommand.SBUS_CMD_CANCEL == command )
        {
            this.logger_.trace( "createStorletTask: " +
                                "received Cancel command");
            ResObj = createCancelTask( dtg );
        }
		else
		{
		    this.logger_.error( "createStorletTask: " + 
		                        command + 
		                        " is not supported" );
		}
		return ResObj;
	}
	
	/*------------------------------------------------------------------------
	 * createExecutionTask
	 * */
	private SExecutionTask createExecutionTask( SBusDatagram dtg )
	                                                   throws StorletException
	{	    
	    ArrayList<StorletInputStream>  inStreams  = 
	                                     new ArrayList<StorletInputStream>();
	    ArrayList<StorletOutputStream> outStreams = 
	                                     new ArrayList<StorletOutputStream>();
	    StorletLogger storletLogger = null;
	    int nFiles = dtg.getNFiles();
	    HashMap<String, String>[] FilesMD = dtg.getFilesMetadata();
	    this.logger_.trace("StorletTask: Got " + nFiles + " fds");
            OutputStream taskIdOut = null;
	    for( int i = 0; i < nFiles; ++i ) 
	    {
	        String strFDtype = FilesMD[i].get( "type" );
        	// type is a metadata field used internally, and it should not
        	// make it further to the Storlet invocation

	        FilesMD[i].remove("type");
                if (strFDtype.equals("SBUS_FD_OUTPUT_TASK_ID"))
		{
                    taskIdOut = new FileOutputStream( dtg.getFiles()[i] );
		}
	        else if( strFDtype.equals("SBUS_FD_INPUT_OBJECT") )
	        {
	            this.logger_.trace( "createStorletTask: fd " + 
	                                i + 
	                                " is of type SBUS_FD_INPUT_OBJECT");
	            inStreams.add(
	                    new StorletInputStream( 
	                                            dtg.getFiles()[i], 
	                                            dtg.getFilesMetadata()[i]));
	        }
	        else if( strFDtype.equals("SBUS_FD_OUTPUT_OBJECT") ) 
	        {
	            this.logger_.trace( 
	                    "createStorletTask: fd " + 
	                    i + 
	                    " is of type SBUS_FD_OUTPUT_OBJECT" );
	            String strNextFDtype =dtg.getFilesMetadata()[i+1].get("type");
	            if( !strNextFDtype.equals("SBUS_FD_OUTPUT_OBJECT_METADATA") )
	            {
	                this.logger_.error( 
	                        "StorletTask: fd " + 
	                        (i+1) +
	                        " is not SBUS_FD_OUTPUT_OBJECT_METADATA " + 
	                        " as expected" );
	            } else {
		            this.logger_.trace( 
		                    "createStorletTask: fd " + 
		                    (i+1) + 
		                    " is of type SBUS_FD_OUTPUT_OBJECT_METADATA" );
	            }
	            outStreams.add( 
	                    new StorletObjectOutputStream(
	                                               dtg.getFiles()[i], 
	                                               dtg.getFilesMetadata()[i], 
	                                               dtg.getFiles()[i+1] ) );
	            ++i;
	        }
	        else if( strFDtype.equals( "SBUS_FD_LOGGER" ) ) 
	        {
	            this.logger_.trace( "createStorletTask: fd " + 
	                                i + " is of type SBUS_FD_LOGGER" );
	            storletLogger = new StorletLogger( dtg.getFiles()[i] );
	        }
	        else if( strFDtype.equals( "SBUS_FD_OUTPUT_CONTAINER") ) 
	        {
	            this.logger_.trace( 
	                    "createStorletTask: fd " + 
	                    i + 
	                    " is of type SBUS_FD_OUTPUT_CONTAINER" );
	            this.logger_.trace( 
	                    "createStorletTask: md is" + 
	                    dtg.getFilesMetadata()[i].toString() );
	            outStreams.add( 
	                    new StorletContainerHandle(
	                            dtg.getFiles()[i], 
	                            dtg.getFilesMetadata()[i],
	                            requestsTable_));
	        }
	        else
	            this.logger_.error( "createStorletTask: fd " + i + 
	                                " is of unknown type " + strFDtype );
	    }
	    return new SExecutionTask( storlet_, 
                                         inStreams, 
                                         outStreams,
                                         taskIdOut,
                                         dtg.getExecParams(), 
                                         storletLogger, 
                                         logger_ );
	}

    /*------------------------------------------------------------------------
     * createDescriptorTask
     * */
    private SDescriptorTask createDescriptorTask( SBusDatagram dtg )
    {
        SDescriptorTask ResObj = null;
        String strKey = "";
        boolean bStatus = true;

        if( 2 != dtg.getNFiles() )
        {
            this.logger_.error( "createDescriptorTask: " + 
                                "Wrong fd count for descriptor command. "+
                                "Expected 2, got " + dtg.getNFiles() );
            bStatus = false;
        }
        this.logger_.trace( "createDescriptorTask: #FDs is good" );

        if( bStatus )
        {
            strKey = dtg.getExecParams().get("key");
            if( null == strKey )
            {
                this.logger_.error( "createDescriptorTask: "+
                                    "No key in params");
                bStatus = false;
            }
            this.logger_.trace("createDescriptorTask: key is good");
        }
        
        if( bStatus )
        {
        	// type is a metadata field used internally, and it should not
        	// make it further to the Storlet invocation
            String strFDType = dtg.getFilesMetadata()[0].get("type");
            dtg.getFilesMetadata()[0].remove("type");
            if( !strFDType.equals( "SBUS_FD_OUTPUT_OBJECT" ) )
            {
                this.logger_.error( "createDescriptorTask: " + 
                             "Wrong fd type for descriptor command. "+
                             "Expected SBUS_FD_OUTPUT_OBJECT " + 
                             " got " + strFDType );
                bStatus = false;
            }
            this.logger_.trace("createStorletTask: " + 
                    "fd metadata is good. Creating object stream");            
        }
        
        if( bStatus )
        {
            StorletObjectOutputStream objStream = 
                    new StorletObjectOutputStream( dtg.getFiles()[0], 
                                                   dtg.getFilesMetadata()[0], 
                                                   dtg.getFiles()[1]);
            // parse descriptor stuff
            this.logger_.trace( "createStorletTask: " + 
                                "Returning StorletDescriptorTask");
            ResObj = new SDescriptorTask( objStream, 
                                                strKey, 
                                                requestsTable_, 
                                                logger_ );
        }
        return ResObj; 
    }

/*------------------------------------------------------------------------
     * createCancelTask
     * */
    private SCancelTask createCancelTask( SBusDatagram dtg )
    {
        SCancelTask ResObj = null;
        String taskId = dtg.getTaskId();
        boolean bStatus = true;

        if( 1 != dtg.getNFiles() )
        {
            this.logger_.error( "createCancelTask: " +
                                "Wrong fd count for descriptor command. "+
                                "Expected 1, got " + dtg.getNFiles() );
            bStatus = false;
        }
        this.logger_.trace( "createCancelTask: #FDs is good" );

        if( bStatus )
        {
            String strFDType = dtg.getFilesMetadata()[0].get("type");
            if( !strFDType.equals( "SBUS_FD_OUTPUT_OBJECT" ) )
            {
                this.logger_.error( "createCancelTask: " +
                             "Wrong fd type for Cancel command. "+
                             "Expected SBUS_FD_OUTPUT_OBJECT " +
                             " got " + strFDType );
                bStatus = false;
            }
            this.logger_.trace("createCancelTask: " +
                    "fd metadata is good. Creating stream");
        }

        if( bStatus )
        {
            OutputStream sOut = new FileOutputStream( dtg.getFiles()[0] );
            // parse descriptor stuff
            this.logger_.trace( "createCancelTask: " +
                                "Returning StorletCancelTask");
            ResObj = new SCancelTask( sOut, logger_, taskId );
        }
        return ResObj;
    }

    /*------------------------------------------------------------------------
     * createPingTask
     * */
    private SPingTask createPingTask( SBusDatagram dtg )
    {
        SPingTask ResObj = null;
        boolean bStatus = true;

        if( 1 != dtg.getNFiles() )
        {
            this.logger_.error( "createPingTask: " + 
                                "Wrong fd count for descriptor command. "+
                                "Expected 1, got " + dtg.getNFiles() );
            bStatus = false;
        }
        this.logger_.trace( "createPingTask: #FDs is good" );
        
        if( bStatus )
        {
            String strFDType = dtg.getFilesMetadata()[0].get("type");
            if( !strFDType.equals( "SBUS_FD_OUTPUT_OBJECT" ) )
            {
                this.logger_.error( "createPingTask: " + 
                             "Wrong fd type for Ping command. "+
                             "Expected SBUS_FD_OUTPUT_OBJECT " + 
                             " got " + strFDType );
                bStatus = false;
            }
            this.logger_.trace("createPingTask: " + 
                    "fd metadata is good. Creating object stream");            
        }
        
        if( bStatus )
        {
            OutputStream sOut = new FileOutputStream( dtg.getFiles()[0] );
            // parse descriptor stuff
            this.logger_.trace( "createPingTask: " + 
                                "Returning StorletPingTask");
            ResObj = new SPingTask( sOut, logger_ );
        }
        return ResObj; 
    }
}
/*============================== END OF FILE ===============================*/

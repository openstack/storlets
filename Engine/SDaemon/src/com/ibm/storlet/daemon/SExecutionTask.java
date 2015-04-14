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
 10-Jul-2014    evgenyl     Refactoring.
 ===========================================================================*/
package com.ibm.storlet.daemon;

import org.slf4j.Logger;

import com.ibm.storlet.common.*;

import java.util.HashMap;
import java.util.ArrayList;

/*----------------------------------------------------------------------------
 * SExecutionTask
 * 
 * Thread pool worker. Wraps File I/O streams for the further 
 * utilization by storlet
 * */
public class SExecutionTask extends SAbstractTask implements Runnable 
{	
	private StorletLogger                  storletLogger_      = null;
	private IStorlet                       storlet_            = null;
	private ArrayList<StorletInputStream>  inStreams_          = null;
	private ArrayList<StorletOutputStream> outStreams_         = null;
	private HashMap<String, String>        executionParams_    = null;
	
	/*------------------------------------------------------------------------
	 * CTOR
	 * */
	public SExecutionTask( IStorlet                        storlet,
	                       ArrayList<StorletInputStream>   instreams,
	                       ArrayList<StorletOutputStream>  outstreams, 
	                       HashMap<String, String>         executionParams, 
	                       StorletLogger                   storletLogger,
	                       Logger                          logger ) 
	{
		super( logger );
		this.storlet_          =   storlet;
		this.inStreams_        =   instreams;
		this.outStreams_       =   outstreams;
		this.executionParams_  =   executionParams;
		this.storletLogger_    =   storletLogger;
		
	}
	
	/*------------------------------------------------------------------------
	 * getters
	 * */
	public ArrayList<StorletInputStream> getInStreams() 
	{
		return inStreams_;
	}

	public ArrayList<StorletOutputStream> getOutStreams() 
	{
		return outStreams_;
	}

	public HashMap<String, String> getExecutionParams() 
	{
		return executionParams_;
	}

	/*------------------------------------------------------------------------
	 * run
	 * 
	 * Actual storlet invocation
	 * */
	@Override
	public void run() 
	{
		try 
		{
			storletLogger_.emitLog("About to invoke storlet");
			storlet_.invoke( inStreams_, outStreams_, 
			                executionParams_, storletLogger_);
			storletLogger_.emitLog("Storlet invocation done");
		} 
		catch( StorletException e ) 
		{
			storletLogger_.emitLog( e.getMessage() );
		}
		finally
		{
		    storletLogger_.Flush();		    
		}
	}
}
/*============================== END OF FILE ===============================*/

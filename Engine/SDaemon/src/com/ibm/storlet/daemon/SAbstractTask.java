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
 ===========================================================================*/
package com.ibm.storlet.daemon;

import org.slf4j.Logger;

/*----------------------------------------------------------------------------
 * SAbstractTask
 * 
 * A common parent object for different Tasks created by STaskFactory
 * */
public class SAbstractTask {

	protected Logger logger;

	public SAbstractTask(Logger logger) {
		this.logger = logger;
	}

}
/* ============================== END OF FILE =============================== */

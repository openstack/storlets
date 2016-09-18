/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2016 All Rights Reserved
 * Copyright Universitat Rovira i Virgili. 2015, 2016 All Rights Reserved
 *
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
package org.openstack.storlet.csv.clauses;

import java.util.List;
import java.util.Vector;

import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public class EmptyClause implements ClauseIf {

    private Vector<ClauseIf> EMPTY_LIST = new Vector<ClauseIf>();
    private EmptyClause singleton = null;

    public EmptyClause() {
        if (singleton == null) {
            singleton = new EmptyClause(" ");
        }
    }

    private EmptyClause(String str) {
        singleton  = this;
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#isLeaf()
     */
    @Override
    public boolean isLeaf() {
        return true;
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#getChildren()
     */
    @Override
    public List<ClauseIf> getChildren() {
        return EMPTY_LIST;
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#isValid()
     */
    @Override
    public boolean isValid(StorletLogger logger, String[] trace_line) {
        return true;
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#getMaxCol()
     */
    @Override
    public int getMaxCol() {
        return 0;
    }

}

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

import java.util.Arrays;

import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public class AndClause extends Clause {

    public AndClause(StorletLogger logger, String[] highLevelClauses) {
        super(logger);
        if (highLevelClauses.length < 2)
            throw new RuntimeException("AndClause necessitates at least 2 clauses! " + Arrays.toString(highLevelClauses));

        for (String nextClauseStr : highLevelClauses) {
            ClauseIf nextClause = parseClause(logger, nextClauseStr);
            addChild(nextClause);
        }
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#isLeaf()
     */
    @Override
    public boolean isLeaf() {
        return false;
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.Clause#toString()
     */
    @Override
    public String toString() {
        return "AND of:\n" + super.toString() + "-----  AND completed -------\n";
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#isValid()
     */
    @Override
    public boolean isValid(StorletLogger logger, String[] trace_line) {
        for (ClauseIf next : getChildren()) {
            if (!next.isValid(logger, trace_line)) {
                return false;
            }
        }
        return true;
    }

}

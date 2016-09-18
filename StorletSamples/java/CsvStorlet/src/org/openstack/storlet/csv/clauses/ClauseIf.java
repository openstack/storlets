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

import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public interface ClauseIf {

    /**
     * This string separates high level clauses where the parent clause is considered as an AND clause
     */
    public final static String HIGH_LEVEL_AND_SEPARATOR = " ";

    /**
     * @return true iff this is a leaf Clause without any child
     */
    public boolean isLeaf();

    /**
     * @return the list of the clause children
     */
    public List<ClauseIf> getChildren();

    /**
     * @return the logical evaluation of this for argument trace_line
     */
    public boolean isValid(StorletLogger logger, String[] trace_line);

    /**
     * @return the maximum column index addressed within this ClauseIf object
     */
    public int getMaxCol();

}

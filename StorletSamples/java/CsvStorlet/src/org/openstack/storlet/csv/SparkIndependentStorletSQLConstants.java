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
package org.openstack.storlet.csv;

public interface SparkIndependentStorletSQLConstants {

    /*
     * Following constants are used to build the predicate corresponding to the WHERE clause of
     * the SQL query
     */
    public static final String AND          = "And";
    public static final String OR           = "Or";
    public static final String EQUAL        = "EqualTo";
    public static final String NOT_EQUAL    = "NotEqualTo";
    public static final String STARTS_WITH  = "StringStartsWith";
    public static final String ENDS_WITH    = "StringEndsWith";
    public static final String CONTAINS     = "StringContains";
}

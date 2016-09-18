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

public interface PushdownStorletConstants {

    public static final String SWIFT_PUSHDOWN_STORLET_NAME = "CSVStorlet-1.0.jar";
    public static final String SWIFT_PUSHDOWN_STORLET_HEADER_NAME = "X-Run-Storlet";
    public static final String SWIFT_PUSHDOWN_STORLET_PARAM_PREFIX = "X-Storlet-Parameter-";
    public static final String SWIFT_PUSHDOWN_STORLET_QUERY_SEPARATOR = ";";

    // separates parameter name and value in Spark string
    public static final String SWIFT_PUSHDOWN_STORLET_QUERY_PARAM_EQUAL = "=";

    // separates parameter name and value in storlet parameter
    public static final String SWIFT_STORLET_QUERY_PARAM_EQUAL = ":";

    public static final String SWIFT_PUSHDOWN_STORLET_RANGE_START = "start";
    public static final String SWIFT_PUSHDOWN_STORLET_RANGE_END = "end";
    public static final String SWIFT_PUSHDOWN_STORLET_MAX_RECORD_LINE = "max_record_line";
    public static final String SWIFT_PUSHDOWN_STORLET_IS_FIRST_PARTITION = "first_partition";
    public static final String SWIFT_PUSHDOWN_STORLET_SELECTED_COLUMNS = "selected_columns";
    public static final String SWIFT_PUSHDOWN_STORLET_WHERE_CLAUSE = "where_clause";

    public static final String SWIFT_PUSHDOWN_STORLET_RECORD_DELIMITER = "delimiter";
    public static final String SWIFT_PUSHDOWN_STORLET_RECORD_COMMENT = "comment";
    public static final String SWIFT_PUSHDOWN_STORLET_RECORD_QUOTE = "quote";
    public static final String SWIFT_PUSHDOWN_STORLET_RECORD_ESCAPTE = "escape";

    public static final String SWIFT_PUSHDOWN_STORLET_DYNAMIC_DEBUG =
            "X-Storlet-DynamicDebug";

    public static final String SWIFT_PUSHDOWN_STORLET_REQUESTED_RANGE_SEPARATOR = "_";


    public static final String DEFAULT_RECORD_DELIMITER = "\n";
    public static final String DEFAULT_TOKEN_DELIMITER = ",";
    public static final String DEFAULT_PREDICATE = "";
    public static final String DEFAULT_DYNAMIC_DEBUG = "0";
    public static final String DEFAULT_COLUMNS = "";
    public static final String DEFAULT_FILE_ENCRYPTION = "UTF-8";
    public static final long   DEFAULT_STREAM_BUFFER_LENGTH = 64 * 1024;  // 64 K

    public static final String COLUMNS_SEPARATOR = ",";   // in fact used in upper packages
}

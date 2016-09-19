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

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public class ReaderEnv implements PushdownStorletConstants, SparkIndependentStorletSQLConstants {

    // General parameters names:

    private static final String IS_STORLET_INVOCATION = "isStorletInvocation";  // False when run from within Eclipse

    public static final String FIELD_PREFIX      = "";

    // Data member:
    /**
     * The list of the requested columns
     * If empty, this means that all columns are requested
     *
     */
    private String[] selectedFields;
    private int maxSelectedIndex = -1;  // specifies the highest requested column index, stays as -1 if all columns requested

    private String theWhereClause;
    private Map<String, String> theParamMap;
    private StorletLogger logger;

    private long startRangePosition;   // the file offset from which the range is defined
    private long endRangePosition;     // the end file position for which the range is defined
    private int maxRecordLine;         // the maximum length of a record
    private boolean fistPartition;     // is this the first partition
    private long dynamicDebug;         // a request dependent debug value which permits to force logging of certain events

    /**
     * Non Storlet invocation path
     * @param parameters
     * @throws StorletException
     */
    static public ReaderEnv getReaderEnv(final String[] args, final StorletLogger logger) throws StorletException {
        Map<String, String> theMap = buildParamMap(args, logger, false);
        return new ReaderEnv(theMap, logger);
    }

    /**
     * Storlet invocation path
     * @param parameters
     * @param log
     * @param storletInvocation
     * @throws StorletException
     */
    public ReaderEnv(final Map<String, String> parameters, final StorletLogger logger) throws StorletException {
        theParamMap = parameters;
        this.logger = logger;
        setDataMemberValues(theParamMap);
    }

    /**
     * @param log
     * @param isRealStorletInvocation
     * @param theParamMap
     * @return a Map of the options
     */
    static private Map<String, String> buildParamMap(String[] args, StorletLogger log, boolean isRealStorletInvocation) {
        final Map<String, String> theMap = new HashMap<String, String>();

        // Parse the passed parameters defining the behavior of the CSV parser:
        for (String nextArg : args) {
            if (nextArg.contains("=")) {
                String[] arr = nextArg.split("=");
                if (arr.length != 2) {
                    Utils.doubleLogPrint(log,"Seems we got a bad formatted parameter! " + nextArg);
                } else {
                    theMap.put(arr[0].trim(), arr[1]);
                }
            }
        }

        theMap.put(IS_STORLET_INVOCATION, Boolean.toString(isRealStorletInvocation));

        return theMap;
    }

    private void setDataMemberValues(final Map<String, String> theMap) throws StorletException {
        // List of selected fields:  (permits to requests columns by field header name)
        {
            String theFields = Utils.getParam(theMap, SWIFT_PUSHDOWN_STORLET_SELECTED_COLUMNS, DEFAULT_COLUMNS, logger,  false);
            String[] requestedFieldsStrings = null;
            if (theFields != null && theFields.length()>0) {
                requestedFieldsStrings = theFields.split(COLUMNS_SEPARATOR);
                Utils.doubleLogPrint(logger," Requested fields: "  + Arrays.toString(requestedFieldsStrings));
            }

            if (theFields != null && theFields.length()>0) {

                if (requestedFieldsStrings != null && requestedFieldsStrings.length > 0) {
                    int nextIndex = 0;
                    selectedFields = new String[requestedFieldsStrings.length];

                    for (String nextStringNumber : requestedFieldsStrings) {
                        try {
                            int nextParsedNumber = Integer.parseInt(nextStringNumber);
                            selectedFields[nextIndex++] = getFieldName(nextParsedNumber);
                            if (nextParsedNumber > maxSelectedIndex) {
                                maxSelectedIndex = nextParsedNumber;
                            }
                        } catch (NumberFormatException nfe) {
                            throw new StorletException("The argument specifying the selected fields " + theFields + " contains a column index which could not be parsed as an integer: " + nextStringNumber);
                        }
                    }
                    Utils.doubleLogPrint(logger," max selected index 1 is "  + maxSelectedIndex);
                }

            }
        }


        // The dynamic debug level:
        {
            String dynamicDebugStr = Utils.getParam(theMap, SWIFT_PUSHDOWN_STORLET_DYNAMIC_DEBUG, DEFAULT_DYNAMIC_DEBUG, logger, false);
            try {
                Utils.doubleLogPrint(logger, "dynamicDebugStr string = " + dynamicDebugStr);
                dynamicDebug = Long.parseLong(dynamicDebugStr);
            } catch (NumberFormatException e) {
                dynamicDebug = 0;
            }

        }

        // The WHERE clause:
        {
            theWhereClause = Utils.getParam(theMap, SWIFT_PUSHDOWN_STORLET_WHERE_CLAUSE, DEFAULT_PREDICATE, logger, false);
            Utils.doubleLogPrint(logger, "theWhereClause = " + theWhereClause);
        }

        // The requested range:
        {
            startRangePosition = getLongParam(SWIFT_PUSHDOWN_STORLET_RANGE_START, -1);
            if (startRangePosition == -1) {
                throw new StorletException("Start position is either missing or malformed");
            }

            endRangePosition = getLongParam(SWIFT_PUSHDOWN_STORLET_RANGE_END, -1);
            if (endRangePosition == -1) {
                throw new StorletException("End position is either missing or malformed");
            }
        }

        // Max record line
        {
            maxRecordLine = getIntParam(SWIFT_PUSHDOWN_STORLET_MAX_RECORD_LINE, -1);
            if (maxRecordLine == -1) {
                throw new StorletException("Max Record Line is either missing or malformed");
            }
         }

         // First Partition
         {
            String fistPartitionString = Utils.getParam(theParamMap, SWIFT_PUSHDOWN_STORLET_IS_FIRST_PARTITION, "", logger);
            if (fistPartitionString.equals("")) {
                throw new StorletException("First partition is missing");
            }
            try {
                fistPartition = Boolean.parseBoolean(fistPartitionString);
            } catch (Exception ex) {
                throw new StorletException("First partition is malformed");
            }
         }

    }

    private String getFieldName(int colIndex) {
        // returns the concatenation of default selected column prefix and the requested index
        return FIELD_PREFIX + colIndex;
    }

    public String getTheWhereClause() {
        return theWhereClause;
    }

    public Map<String, String> getTheParams() {
        return theParamMap;
    }

    /**
     * @param key
     * @return associated value
     * @throws RuntimeException if the value is missing!
     */
    public String getParam(String key) {
        return getParam(key, null);
    }

    /**
     * @param key
     * @param defaultValue
     * @return
     */
    public String getParam(String key, String defaultValue) {
        return Utils.getParam(theParamMap, key, defaultValue, logger);
    }

    /**
     * @param key
     * @param defaultValue
     * @return
     */
    public long getLongParam(String key, long defaultValue) {
        String valString = Utils.getParam(theParamMap, key, Long.toString(defaultValue), logger);
        if (valString == null)
            return defaultValue;
        else {
            long retVal = defaultValue;
            try {
                retVal = Long.parseLong(valString);
            } catch (NumberFormatException nfe) {
                // NOP
            }
            return retVal;
        }
    }

    /**
     * @param key
     * @param defaultValue
     * @return
     */
    public int getIntParam(String key, int defaultValue) {
        String valString = Utils.getParam(theParamMap, key, Integer.toString(defaultValue), logger);
        if (valString == null)
            return defaultValue;
        else {
            int retVal = defaultValue;
            try {
                retVal = Integer.parseInt(valString);
            } catch (NumberFormatException nfe) {
                // NOP
            }
            return retVal;
        }
    }

    public int[] getSelectedFields() {
        if (selectedFields == null) {
            return null;
        }
        if ( selectedFields.length == 0) {
            return null;
        }
        if (selectedFields[0].equals("*")) {
            return null;
        }

        int[] arr = new int[selectedFields.length];
        int index = 0;
        for (String nextCol : selectedFields) {
            arr[index++] = Integer.parseInt(nextCol);
        }
        return arr;
    }

    public int getMaxRecordLine() {
        return maxRecordLine;
    }

    public boolean getIsFirstPartition() {
        return fistPartition;
    }

    public long getStartRangePosition() {
        return startRangePosition;
    }

    public long getEndRangePosition() {
        return endRangePosition;
    }

    public long getDynamicDebug() {
        return dynamicDebug;
    }

}

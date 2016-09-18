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

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Map;

import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public class Utils {


    public static String getParam(final Map<String, String> paramMap, final String paramName, final String defaultValue, final StorletLogger log) {
        return getParam(paramMap, paramName, defaultValue, log, false);
    }

    /**
     * @param paramMap the Map of the parameters:  associates parameter names to parameter values
     * @param paramName the name of the parameter
     * @param defaultValue if null no default value and an exception will be thrown if the parameter value is missing in paramMap
     * @param isChar true if the parameter is a char
     * @return the String value of the parameter
     */
    public static String getParam(final Map<String, String> paramMap, final String paramName, final String defaultValue, final StorletLogger logger, final boolean isChar) {
        String val = paramMap.get(paramName);

        if (val == null || val.length() == 0) {
            if (defaultValue == null) {
                throw new RuntimeException("Missing value for parameter " + paramName);
            }
            val = defaultValue;
        } else if (isChar && val.length()>1) {
            throw new RuntimeException(val + " : the value given for parameter " + paramName + " should not have more than a single character!");
        }
        doubleLogPrint(logger, " value for " + paramName + " is:" + val);
        return val;
    }

    public static boolean getBoolean(Map<String, String> parameters, String paramName, boolean paramDefaultValue, final StorletLogger log) {
        String paramValue = getParam(parameters, paramName, (new Boolean(paramDefaultValue)).toString(), log, Boolean.FALSE);
        return Boolean.parseBoolean(paramValue);
    }

    public static void doubleLogPrint(StorletLogger logger, String printString) {
        if (logger != null)
            logger.emitLog(printString);
        System.out.println(printString);
    }

    public static String extractParam(final String[] args, final String searchedKey, final String missingTxt) {
        for (String nextArg :args) {
            if (nextArg != null && nextArg.startsWith(searchedKey)) {
                String[] tokens = nextArg.split("=");
                if (tokens.length > 1) {
                    return tokens[1];
                } else {
                    throw new RuntimeException(missingTxt +  ": key was found but without value!: " + nextArg);
                }
            }
        }

        return null;
    }


    public static String getStackTrace(Exception e) {
        if (e == null)
            return null;

        StringWriter sw = new StringWriter();
        e.printStackTrace(new PrintWriter(sw));
        return sw.toString();
    }

}

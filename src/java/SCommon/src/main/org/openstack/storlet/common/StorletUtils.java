/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
 * Copyright (c) 2010-2016 OpenStack Foundation
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

package org.openstack.storlet.common;

public class StorletUtils {
    public static final String getClassFolder(
            @SuppressWarnings("rawtypes") Class o) {
        String strResult = "";
        String strJarPath = o.getProtectionDomain().getCodeSource()
                .getLocation().getPath();
        String strSep = java.io.File.separator;
        String[] strSubfolders = strJarPath.split(strSep);
        // The content of strSubfolders is something like:
        // "/home" "swift" "SomeStorlet" "SomeStorlet-1.0.jar"
        // The first token contains separator, the last shall be thrown.
        strResult = strSubfolders[0];
        int nOfSubF = strSubfolders.length - 1;
        for (int i = 1; i < nOfSubF; ++i) {
            strResult = strResult + strSep + strSubfolders[i];
        }
        return strResult;
    }
}

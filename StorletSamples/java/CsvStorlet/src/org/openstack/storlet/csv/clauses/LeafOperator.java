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

public enum LeafOperator {
    EQUAL("EqualTo") {
        @Override public boolean isValid(String clauseOp, String lineVal) {
            if (clauseOp == null)
                return lineVal == null || lineVal.trim().length() == 0;
            return clauseOp.equals(lineVal);
        }
    },
    NOT_EQUAL("NotEqualTo"){
        @Override public boolean isValid(String clauseOp, String lineVal) {
            if (clauseOp == null)
                return lineVal != null && lineVal.trim().length() > 0;
                return !clauseOp.equals(lineVal);
        }
    },
    STARTS_WITH("StringStartsWith"){
        @Override public boolean isValid(String clauseOp, String lineVal) {
            if (clauseOp == null || clauseOp.length() == 0)
                return true;
            if (lineVal == null || lineVal.length() == 0)
                return false;
            return lineVal.startsWith(clauseOp);
        }
        @Override public String transform(String operand) {
            if (operand == null || !operand.endsWith("%"))
                return operand;
            else
                return operand.substring(0, operand.length()-1);
        }
    },
    ENDS_WITH("StringEndsWith") {
        @Override public boolean isValid(String clauseOp, String lineVal) {
            if (clauseOp == null || clauseOp.length() == 0)
                return true;
            if (lineVal == null || lineVal.length() == 0)
                return false;
            return lineVal.endsWith(clauseOp);
        }
        @Override public String transform(String operand) {
            if (operand == null || !operand.startsWith("%"))
                return operand;
            else
                return operand.substring(1, operand.length());
        }
    },
    CONTAINS("StringContains")  {
        @Override public boolean isValid(String clauseOp, String lineVal) {
            if (clauseOp == null || clauseOp.length() == 0)
                return true;
            if (lineVal == null || lineVal.length() == 0)
                return false;
            return lineVal.contains(clauseOp);
        }
        @Override public String transform(String operand) {
            if (operand == null || !operand.startsWith("%") || !operand.endsWith("%"))
                return operand;
            else
                return operand.substring(1, operand.length()-1);
        }
    };

    private final String opLabel;

    LeafOperator(String label) {
        this.opLabel = label;
    }

    public String getLeafOpLabel() {
        return opLabel;
    }

    public abstract boolean isValid(String clauseOp, String lineVal);

    public String transform(String operand) {
        return operand;
    }
}

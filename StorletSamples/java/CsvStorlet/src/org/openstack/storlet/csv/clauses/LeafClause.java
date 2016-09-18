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

import org.openstack.storlet.csv.Utils;
import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public class LeafClause extends Clause {

    private LeafOperator op;  // the Operator of the Clause
    private int clauseColumnIndex;       // its column index of the clause
    private String clauseOperand;    // its clause operand

    public LeafClause(StorletLogger logger, String clauseStr) {
        super(logger);
        parse(clauseStr);
        Utils.doubleLogPrint(logger,"LeafClause constructor: " + op.getLeafOpLabel() + " for column " + clauseColumnIndex + " and with operand " + clauseOperand);
    }

    @Override
    public String toString() {
        return "Clause:  op = " + op.getLeafOpLabel() + " column #  =" + clauseColumnIndex + " Operand = "  + clauseOperand;
    }

    public boolean isValidClause(StorletLogger logger, String[] trace_line) {
        String lineOperand;
        try {
            lineOperand = trace_line[clauseColumnIndex];
        } catch( ArrayIndexOutOfBoundsException e) {
            Utils.doubleLogPrint(logger, "ArrayIndexOutOfBoundsException occurred, for trace_line = " +
                    ( ( trace_line == null) ? " null " : Arrays.toString(trace_line) ) + " and clause = " + this);
            throw e;
        }
        return (op.isValid(clauseOperand, lineOperand));
    }

    public int getMaxCol() {
        return clauseColumnIndex;
    }

    void parse(String clauseStr) {
        Utils.doubleLogPrint(logger,"LeafClause.parse for " + clauseStr);
        LeafOperator theOp;

        if (clauseStr.startsWith(LeafOperator.EQUAL.getLeafOpLabel())) {
            theOp = LeafOperator.EQUAL;
        } else if (clauseStr.startsWith(LeafOperator.NOT_EQUAL.getLeafOpLabel())) {
            theOp = LeafOperator.NOT_EQUAL;
        } else if (clauseStr.startsWith(LeafOperator.STARTS_WITH.getLeafOpLabel())) {
            theOp = LeafOperator.STARTS_WITH;
        } else if (clauseStr.startsWith(LeafOperator.ENDS_WITH.getLeafOpLabel())) {
            theOp = LeafOperator.ENDS_WITH;
        } else if (clauseStr.startsWith(LeafOperator.CONTAINS.getLeafOpLabel())) {
            theOp = LeafOperator.CONTAINS;
        } else {
            throw new RuntimeException("Unexpected clause operator " + clauseStr);
        }

        String[] ops = clauseStr.substring(theOp.getLeafOpLabel().length()).split(",");
        int clauseIndex;
        try {
            clauseIndex = Integer.parseInt(ops[0].substring(1)); // remove the "("
        } catch (NumberFormatException  e) {
            Utils.doubleLogPrint(logger,"parseClause for " + clauseStr +  " encountered a NumberFormatException when trying to convert " + ops[0].substring(1) + " to int");
            throw e;
        }
        clauseOperand = ops[1].substring(0, ops[1].length()-1); // remove the ")"
        op = theOp;
        clauseColumnIndex = clauseIndex;
    }

    @Override
    public boolean isLeaf() {
        return true;
    }

    @Override
    public boolean isValid(StorletLogger logger, String[] trace_line) {
        String lineOperand;
        try {
            lineOperand = trace_line[clauseColumnIndex];
        } catch( ArrayIndexOutOfBoundsException e) {
            Utils.doubleLogPrint(logger, "ArrayIndexOutOfBoundsException occurred, for trace_line = " +
                    ( ( trace_line == null) ? " null " : Arrays.toString(trace_line) ) + " and clause = " + this);
            throw e;
        }
        return (op.isValid(clauseOperand, lineOperand));
    }

}

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

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.openstack.storlet.csv.Utils;
import org.openstack.storlet.common.StorletLogger;

/**
 * @author moatti
 *
 */
public abstract class Clause implements ClauseIf {
    private static final int UNINITIALIZED = -12345;

    final static private char COMMA = ',';
    final static private String COMMA_STRING = ",";
    final static private String COMMA_REPLACE_STRING = "HJ3Y5XMC";  // a random rare string which obviously does not contains a comma
    private static final Set<Character> COMMA_INHIBITORS_START = new HashSet<Character>();
    private static final Set<Character> COMMA_INHIBITORS_END = new HashSet<Character>();

    private int maxCol = UNINITIALIZED;
    private List<ClauseIf> children = null;

    protected StorletLogger logger;

    static {
        COMMA_INHIBITORS_START.add('(');
        COMMA_INHIBITORS_START.add('[');
        COMMA_INHIBITORS_END.add(')');
        COMMA_INHIBITORS_END.add(']');
    }

    public Clause(StorletLogger logger) {
        this.logger = logger;
    }

    protected void addChild(ClauseIf nextChild) {
        if (children == null)
            children = new ArrayList<ClauseIf>();
        children.add(nextChild);
    }

    @Override
    public List<ClauseIf> getChildren() {
        return children;
    }

    /* (non-Javadoc)
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {
        StringBuffer sb = new StringBuffer();

        for (ClauseIf nextChild : this.getChildren()) {
            sb.append(nextChild.toString());
            sb.append("\n");
        }

        return sb.toString();
    }

    /* (non-Javadoc)
     * @see org.openstack.storlet.csv.ClauseIf#getMaxCol()
     */
    @Override
    public int getMaxCol() {
        if (maxCol == UNINITIALIZED) {
            maxCol = 0;
            for (ClauseIf nextChild : this.getChildren()) {
                int newVal = nextChild.getMaxCol();
                if (newVal > maxCol)
                    maxCol = newVal;
            }
        }
        return maxCol;
    }

    static public ClauseIf parseClause(StorletLogger logger, String clauseStr) {
        // Assumption1: clauseStr appears as a list of high Level Clauses separated by the space character
        // Assumption2: within high level clauses, AND is marked by:  And(subClause1,subClause2)
        // Assumption3: within high level clauses, OR  is marked by:   Or(subClause1,subClause2)
        // Here are some examples:

        // sqlContext.sql("select count(CaseID) from data where (Status like 'Closed' and CaseID like '%1%' and CaseID like '%3%')")
        // whereClause = EqualTo(2,"Closed")XYZYXStringContains(0,"1")XYZYXStringContains(0,"3")
        // where (Status like 'Open' or CaseID like '%1%' or CaseID like '%3%'  or CaseID like '%5%')")
        // whereClause = Or(Or(Or(EqualTo(2,Open),StringContains(0,1)),StringContains(0,3)),StringContains(0,5))

        // where ((Status like 'Open' or CaseID like '%1%') and CaseID like '%3%')")
        // whereClause = Or(EqualTo(2,Open),StringContains(0,1)) StringContains(0,3)

        // where ((Status like 'Closed' and CaseID like '%1%') or (CaseID like '%3%' and CaseID like '%4%' ) )")
        // WhereClause = Or(And(EqualTo(2,Closed),StringContains(0,1)),And(StringContains(0,3),StringContains(0,4)))

        // where ((Status like 'Closed' or CaseID like '%1%') and (CaseID like '%3%' or CaseID like '%4%' ) )")
        // WhereClause = Or(EqualTo(2,Closed),StringContains(0,1)) Or(StringContains(0,3),StringContains(0,4))

        // where ((Status like 'Closed' or CaseID like '%1%') and (CaseID like '%3%' or CaseID like '%4%' )  and (CaseID like '%5%' and CaseID like '%6%' ) )")
        // WhereClause = Or(EqualTo(2,Closed),StringContains(0,1)) Or(StringContains(0,3),StringContains(0,4)) StringContains(0,5) StringContains(0,6)

        // where ((Status like 'Closed' and CaseID like '%1%') or (CaseID like '%3%' and CaseID like '%4%' ) )")
        // WhereClause = Or(And(EqualTo(2,Closed),StringContains(0,1)),And(StringContains(0,3),StringContains(0,4)))

        // where  ((Status like 'Closed' and CaseID like '%1%' and CaseID like '%2%') or (CaseID like '%3%' and CaseID like '%4%' ) )")
        // WhereClause = Or(And(And(EqualTo(2,Closed),StringContains(0,1)),StringContains(0,2)),And(StringContains(0,3),StringContains(0,4)))

        if (clauseStr == null) {
            Utils.doubleLogPrint(logger,"WARNING null clause string passed to parseClause!");
            return new EmptyClause();
        }

        clauseStr = clauseStr.trim();
        if (clauseStr.length() == 0) {
            Utils.doubleLogPrint(logger,"WARNING trimmed clause string passed to parseClause is empty!");
            return new EmptyClause();
        }

        ClauseIf retClause;


        // First we find out the high level clauses separated by space characters.
        // If we find out more than 2 high level clauses, we will issue an AndClause:
        String[] highLevelAndClauses = clauseStr.split(HIGH_LEVEL_AND_SEPARATOR);
        Utils.doubleLogPrint(logger, highLevelAndClauses.length + " high level clauses found for " + clauseStr);

        if (highLevelAndClauses.length > 1) {
            retClause = new AndClause(logger, highLevelAndClauses);
        } else {
            String clauseString = highLevelAndClauses[0];

            LogicalOperator op = LogicalOperator.NONE;
            if (clauseString.startsWith(LogicalOperator.OR.getOpLabel())) {
                op = LogicalOperator.OR;
            } else if (clauseString.startsWith(LogicalOperator.AND.getOpLabel())) {
                op = LogicalOperator.AND;
            }

            // First, remove if needed the opString and the parenthesis:
            if (op != LogicalOperator.NONE) {
                String whereStringTmp = clauseString.substring(op.getOpLabel().length()+1, clauseString.length()-1);
                whereStringTmp = replaceNonRelevantCommas(whereStringTmp);
                Utils.doubleLogPrint(logger,"Parsing whereStringOr = " + whereStringTmp);
                String[] clauseParts = whereStringTmp.split(",");
                clauseParts = replaceBackCommas(logger, clauseParts);
                Utils.doubleLogPrint(logger,"The clause parts are = " + Arrays.toString(clauseParts));

                if (op == LogicalOperator.AND) {
                    retClause = new AndClause(logger, clauseParts);
                } else {  // op == LogicalOperator.OR
                    retClause = new OrClause(logger, clauseParts);
                }
            } else {
                String[] orParts = new String[1];
                orParts[0] = clauseString;
                retClause = new LeafClause(logger, clauseString);
            }
        }

        Utils.doubleLogPrint(logger,"parseClause for " + clauseStr + " returns\n" + retClause);
        return retClause;
    }

    /**
     * This method will replace all COMMA that are within () with COMMA_REPLACE_STRING
     * @param whereStringOr
     * @return
     */
    static private String replaceNonRelevantCommas(String whereStringOr) {
        if (whereStringOr == null || whereStringOr.length() == 0)
            return whereStringOr;

        char[] charArray = whereStringOr.toCharArray();
        boolean[] inhibited = new boolean[charArray.length];

        int encounteredInhibitors = 0;

        for (int index=0; index<charArray.length; index++) {
            char theChar = charArray[index];
            if (COMMA_INHIBITORS_START.contains(theChar)) {
                encounteredInhibitors++;
            } else if (COMMA_INHIBITORS_END.contains(theChar)) {
                encounteredInhibitors--;
            }
            inhibited[index] = encounteredInhibitors>0;
        }

        StringBuffer sb = new StringBuffer();

        // We now replace all commas for the non inhibited chars:
        for (int index=0; index<charArray.length; index++) {
            char theChar = whereStringOr.charAt(index);
            if (inhibited[index]) {
                if (theChar == COMMA) {
                    sb.append(COMMA_REPLACE_STRING);
                } else {
                    sb.append(theChar);
                }
            } else { // not inhibited, we leave theChar as is:
                sb.append(theChar);
            }
        }

        return sb.toString();
    }

    static private String[] replaceBackCommas(StorletLogger logger, String[] orParts) {
        String[] rets = new String[orParts.length];

        int index = 0;
        for (String next : orParts) {
            if (next != null)
                rets[index++] = next.replaceAll(COMMA_REPLACE_STRING, COMMA_STRING);
            else {
                Utils.doubleLogPrint(logger,"WARNING orParts[" + index + "] is null");
                index++;
            }
        }

        return rets;
    }

}





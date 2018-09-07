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

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.nio.ByteBuffer;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Date;
import java.util.Map;

import org.openstack.storlet.csv.clauses.Clause;
import org.openstack.storlet.csv.clauses.ClauseIf;
import org.openstack.storlet.common.IStorlet;
import org.openstack.storlet.common.StorletException;
import org.openstack.storlet.common.StorletInputStream;
import org.openstack.storlet.common.StorletLogger;
import org.openstack.storlet.common.StorletObjectOutputStream;
import org.openstack.storlet.common.StorletOutputStream;

/**
 *
 * @author Josep Sampe, Yosef Moatti
 *
 */

public class CSVStorlet implements IStorlet, PushdownStorletConstants, SparkIndependentStorletSQLConstants{

    /**
     * Current version of the storlet supports either a single And clause or a single Or clause or a simple clause
     * Where an "And" or "Or" clause is build out of 2 simple clauses
     *
     * In order to have good performance we hard coded the "And" and "Or" clauses through the ands and Ors and ands/ors Part0/1 4 strings
     */
    private ClauseIf theClause;

    private void finalClose(InputStream is, OutputStream os, BufferedReader br) {
        try {
            if (is != null) is.close();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
        try {
            if (os != null) os.close();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
        try {
            if (br != null) br.close();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

    public void invoke(ArrayList<StorletInputStream> inStreams, ArrayList<StorletOutputStream> outStreams,
                    Map<String, String> parameters, StorletLogger logger) throws StorletException {

            Date theDate  = Calendar.getInstance().getTime();
            long startTime = theDate.getTime();
            Utils.doubleLogPrint(logger,">>>>>>> Invoke starting .... at " + theDate);

            ReaderEnv env = new ReaderEnv(parameters, logger);

            StorletInputStream sis = inStreams.get(0);
            InputStream inputStream = sis.getStream();

            StorletObjectOutputStream storletObjectOutputStream = (StorletObjectOutputStream)outStreams.get(0);
            OutputStream outputStream = storletObjectOutputStream.getStream();

            int[] select;
            String where_string;
            BufferedReader br = null;

            long processedBytes = 0;
            long invalidCount = 0;  // counts the number of rows which were found not valid:
            long validCount = 0;  // counts the number of rows which were found valid:
            long probablyMalformedLines = 0; // counts the number of lines which cause an exception while being analyzed
            long lineWithoutEnoughFields = 0; // counts the lines which are too short to be checked with predicate
            String firstLine = "INITIAL_VALUE1";
            String lastValidLine = "INITIAL_VALUE2";
            String charset = DEFAULT_FILE_ENCRYPTION;

            //GET PARAMETERS
            long rangeBytesLeft = -2;
            int maxPredicateIndex = -1;
            final boolean columnSelectionActivated;
            final String recordSeparator;
            final byte[] recordSeparatorBytes;
            int recordSeparatorBytesLen;
            try {
                    select = env.getSelectedFields();
                    where_string = env.getTheWhereClause();

                    Utils.doubleLogPrint(logger,"where_string = " + where_string + " select = " + ((select == null) ? "null" : Arrays.toString(select)) );
                    if (where_string != null) {
                            where_string = where_string.trim();
                            // DEBUG only:
                            where_string = where_string.replaceAll("XYZYX", " ");
                    }

                    maxPredicateIndex = analysePredicate(logger, where_string);

                    columnSelectionActivated =  select != null && select.length > 0;
                    recordSeparator = env.getParam(SWIFT_PUSHDOWN_STORLET_RECORD_DELIMITER, DEFAULT_RECORD_DELIMITER);
                    recordSeparatorBytes = recordSeparator.getBytes(charset);
                    recordSeparatorBytesLen = recordSeparatorBytes.length;
                    Utils.doubleLogPrint(logger,"columnSelectionActivated = " + columnSelectionActivated);
             } catch (Exception ex) {
                    Utils.doubleLogPrint(logger,"Failure during input parsing" + ex.getMessage());
                    finalClose(inputStream, outputStream, null);
                    throw new StorletException(ex.getMessage());
             }

             try {
                    // Write Metadata
                    storletObjectOutputStream.setMetadata(sis.getMetadata());
              } catch (Exception ex) {
                    Utils.doubleLogPrint(logger,"Failure during metadata wtiring" + ex.getMessage());
                    finalClose(inputStream, outputStream, null);
                    throw new StorletException(ex.getMessage());
              }

              try {
                    // Init Input stream Reader
                    br = new BufferedReader(new InputStreamReader(inputStream, charset));
              } catch (Exception ex) {
                    Utils.doubleLogPrint(logger,"Failure during input stream reader init" + ex.getMessage());
                    finalClose(inputStream, outputStream, br);
                    throw new StorletException(ex.getMessage());
              }

              String line;
              rangeBytesLeft = env.getEndRangePosition() - env.getStartRangePosition() + 1;
              try {
                    if (env.getIsFirstPartition() == false) {
                            // Discard first (possibly broken) record:
                            line = br.readLine();
                            if (line == null) {
                                    throw new StorletException("Stream fully consumed before reading first line");
                            }
                            int bytesRead = line.getBytes(charset).length + recordSeparatorBytesLen;
                            processedBytes += bytesRead;
                            rangeBytesLeft -= bytesRead;
                            Utils.doubleLogPrint(logger,"Range is prefixed, following first line (broken record) is discarded from processing " + line);
                    }
              } catch (Exception ex) {
                    Utils.doubleLogPrint(logger,"Failure during first line consumption" + ex.getMessage());
                    finalClose(inputStream, outputStream, br);
                    throw new StorletException(ex.getMessage());
              }

              try {
                    // Consume rest of content
                    while ( ((line = br.readLine()) != null)  && (rangeBytesLeft >= -1) ) {
                            final byte[] lineBytes = line.getBytes(charset);
                            int bytesRead = lineBytes.length + recordSeparatorBytesLen;
                            final String[] trace_line;
                            rangeBytesLeft -= bytesRead;
                            processedBytes += bytesRead;

                            if (columnSelectionActivated || (where_string != null && where_string.length() > 0) ) {
                                    // if specific columns have been chosen, or if a predicate has to be evaluated
                                    // we have to convert the line into a vector:
                                    trace_line = line.split(",");
                                    // After measure the performance of the Storlet I found that split function limits its performance.
                                    // Split() is the most expensive operation in each iteration, maybe other technique (String tokenizer
                                    // or other) is better here.
                                    if (trace_line.length < maxPredicateIndex) {
                                            lineWithoutEnoughFields++;
                                            Utils.doubleLogPrint(logger,"Following line has not enough fields to be analysed with requested predicate! " + line);
                                            continue;
                                    }

                            } else {
                                    trace_line = null;
                            }

                            try {
                                    if ( where_string == null || where_string.length() == 0 || theClause.isValid(logger, trace_line)) {
                                            final byte[] appendLine;
                                            if (columnSelectionActivated) {
                                                    appendLine = chooseColumns(trace_line, select).getBytes(charset);
                                            } else {
                                                    appendLine = lineBytes;
                                            }
                                            writeToOutputStream(logger, appendLine, outputStream, recordSeparatorBytes);
                                            validCount++;
                                            lastValidLine = line;
                                            if (validCount == 1) {
                                                    firstLine = line;
                                            }
                                    } else {
                                            invalidCount++;
                                    }
                            } catch( ArrayIndexOutOfBoundsException e) {
                                    Utils.doubleLogPrint(logger," Following line caused ArrayIndexOutOfBoundsException\n" + ">>>>" + line + "<<<<" + "\nstackTrace=\n" + getStackTraceString(e));
                                    probablyMalformedLines++;
                            }
                    }
                    if (rangeBytesLeft > 0) {
                        Utils.doubleLogPrint(logger,"got a null line with more bytes ot read: " + String.valueOf(rangeBytesLeft));
                    }

                    if ( (line == null) && (rangeBytesLeft > 1024)) {
                            Utils.doubleLogPrint(logger, "Premature end of execution. line is null, however, rangeBytesLeft is " + rangeBytesLeft);
                    }
                    Utils.doubleLogPrint(logger, getCompletionMsg(startTime, null, invalidCount, validCount, probablyMalformedLines, lineWithoutEnoughFields, processedBytes, firstLine, lastValidLine, true));
            } catch (UnsupportedEncodingException e) {
                    Utils.doubleLogPrint(logger,"raised UnsupportedEncodingException: " + e.getMessage());
                    throw new StorletException(e.getMessage());
            } catch (IOException e) {
                    String msg = getCompletionMsg(startTime, e, invalidCount, validCount, probablyMalformedLines, lineWithoutEnoughFields, processedBytes, firstLine, lastValidLine, true);

                    Utils.doubleLogPrint(logger,"raised IOException: " + e.getMessage() +  msg);

                    throw new StorletException(e.getMessage());
            } catch (Exception e) {
                    String msg = getCompletionMsg(startTime, e, invalidCount, validCount, probablyMalformedLines, lineWithoutEnoughFields, processedBytes, firstLine, lastValidLine, true);
                    Utils.doubleLogPrint(logger,"raised Exception: " + e.getMessage() + msg);
                    throw new StorletException(e.getMessage());
            } finally {
                    finalClose(inputStream, outputStream, br);
            }
    }

    /**
     * Generates a string which summarizes the most important info concerning this invocation
     *
     * @param startTime
     * @param e
     * @param invalidCount
     * @param validCount
     * @param probablyMalformedLines
     * @param lineWithoutEnoughFields
     * @param processedBytes
     * @param firstLine
     * @param lastValidLine
     * @param shouldGoOn
     * @return
     */
    private String getCompletionMsg(long startTime, Exception e, long invalidCount, long validCount, long probablyMalformedLines, long lineWithoutEnoughFields, long processedBytes, String firstLine, String lastValidLine, boolean shouldGoOn) {
            StringBuffer sb = new StringBuffer();

            Date theDate  = Calendar.getInstance().getTime();
            long duration = theDate.getTime() - startTime;

            sb.append(">>>> StartTime= ");
            sb.append(startTime);
            sb.append(" duration= ");
            sb.append(duration);
            sb.append(" endTime= ");
            sb.append(theDate);
            sb.append(" COUNTS invalid= ");
            sb.append(invalidCount);
            sb.append(" valid= ");
            sb.append(validCount);
            sb.append(" probablyMalformed=");
            sb.append(probablyMalformedLines);
            sb.append(" lineWithoutEnoughFields=");
            sb.append(lineWithoutEnoughFields);
            sb.append(" processedBytes = ");
            sb.append(processedBytes);
            sb.append("\nfirst line =");
            sb.append(firstLine);
            sb.append("\nlastValidLine =");
            sb.append(lastValidLine);
            sb.append(" shouldGoOn = ");
            sb.append(shouldGoOn);

            if (e != null) {
                    sb.append(" EXCEPTION occurred!!!! " + e);
            }


            return sb.toString();
    }

    /**
     * @param logger
     * @param predicateString
     * @return the maximum index in use within predicate
     */
    private int analysePredicate(StorletLogger logger, String predicateString) {
            Utils.doubleLogPrint(logger," analysePredicate for predicateString = " + predicateString);
            theClause = Clause.parseClause(logger, predicateString);
            return theClause.getMaxCol();
    }

    /**
     * Write the passed string followed by a record separator to the outputStream.
     *
     * @param logger
     * @param theString
     * @param outputStream
     * @param recordSeparator
     * @throws IOException
     */
    private void writeToOutputStream(final StorletLogger logger, final byte[] output, final OutputStream outputStream,
                    final byte[] recordSeparator) throws IOException {

            outputStream.write(output, 0, output.length);
            outputStream.write(recordSeparator, 0, recordSeparator.length);
    }

    private String chooseColumns(String[] trace_line, int[] select) throws IOException {
            StringBuffer sb = new StringBuffer();
            final int maxIndex = trace_line.length - 1;
            boolean first = true;

            for(int index = 0; index < select.length; index++){
                    if (select[index] > maxIndex) {
                            continue;  // the line is too short for selecting specified field
                    }

                    if (! first) {
                            sb.append(",");
                    } else {
                            first = false;
                    }
                    sb.append(trace_line[select[index]]);
            }
            return sb.toString();
    }


    private String getStackTraceString(Exception t) {
            java.io.StringWriter sw2 = new java.io.StringWriter();
            t.printStackTrace(new java.io.PrintWriter(sw2));
            return sw2.toString();
    }

}

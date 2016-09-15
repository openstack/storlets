/*
 * Copyright (c) 2015, 2016 OpenStack Foundation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.openstack.storlet.daemon;

import org.slf4j.Logger;

import org.openstack.storlet.common.*;

import java.util.HashMap;
import java.util.ArrayList;
import java.io.IOException;
import java.io.OutputStream;

import java.util.concurrent.Future;

/*----------------------------------------------------------------------------
 * SExecutionTask
 * 
 * Thread pool worker. Wraps File I/O streams for the further
 * utilization by storlet
 * */
public class SExecutionTask extends SAbstractTask implements Runnable {
    private StorletLogger storletLogger_ = null;
    private IStorlet storlet_ = null;
    private ArrayList<StorletInputStream> inStreams_ = null;
    private ArrayList<StorletOutputStream> outStreams_ = null;
    private HashMap<String, String> executionParams_ = null;
    private OutputStream taskIdOut_ = null;
    private String taskId_ = null;
    private HashMap<String, Future> taskIdToTask_ = null;

    public SExecutionTask(IStorlet storlet,
            ArrayList<StorletInputStream> instreams,
            ArrayList<StorletOutputStream> outstreams, OutputStream taskIdOut,
            HashMap<String, String> executionParams,
            StorletLogger storletLogger, Logger logger) {
        super(logger);
        this.storlet_ = storlet;
        this.inStreams_ = instreams;
        this.outStreams_ = outstreams;
        this.executionParams_ = executionParams;
        this.storletLogger_ = storletLogger;
        this.taskIdOut_ = taskIdOut;

    }

    public ArrayList<StorletInputStream> getInStreams() {
        return inStreams_;
    }

    public ArrayList<StorletOutputStream> getOutStreams() {
        return outStreams_;
    }

    public HashMap<String, String> getExecutionParams() {
        return executionParams_;
    }

    public OutputStream getTaskIdOut() {
        return taskIdOut_;
    }

    public void setTaskId(String taskId) {
        taskId_ = taskId;
    }

    public void setTaskIdToTask(HashMap<String, Future> taskIdToTask) {
        taskIdToTask_ = taskIdToTask;
    }

    private void closeStorletInputStreams(){
        for(StorletInputStream stream : inStreams_){
            stream.close();
        }
    }

    private void closeStorletOutputStreams(){
        for(StorletOutputStream stream: outStreams_){
            stream.close();
        }
    }

    private void closeStorletStreams(){
        closeStorletInputStreams();
        closeStorletOutputStreams();
    }

    @Override
    public void run() {
        try {
            storletLogger_.emitLog("About to invoke storlet");
            storlet_.invoke(inStreams_, outStreams_, executionParams_,
                    storletLogger_);
            storletLogger_.emitLog("Storlet invocation done");
            synchronized (taskIdToTask_) {
                taskIdToTask_.remove(taskId_);
            }
        } catch (StorletException e) {
            storletLogger_.emitLog(e.getMessage());
        } finally {
            storletLogger_.close();

            // We make sure all streams are closed
            closeStorletStreams();
        }
    }
}

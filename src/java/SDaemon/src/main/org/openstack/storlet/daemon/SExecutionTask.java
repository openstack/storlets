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
import org.openstack.storlet.daemon.SExecutionManager;

import java.util.ArrayList;
import java.util.HashMap;
import java.io.IOException;
import java.io.OutputStream;

/*----------------------------------------------------------------------------
 * SExecutionTask
 *
 * Thread pool worker. Wraps File I/O streams for the further
 * utilization by storlet
 * */
public class SExecutionTask extends SAbstractTask implements Runnable {
    private StorletLogger storletLogger_ = null;
    private IStorlet storlet_ = null;
    private OutputStream sOut_ = null;
    private ArrayList<StorletInputStream> inStreams_ = null;
    private ArrayList<StorletOutputStream> outStreams_ = null;
    private HashMap<String, String> executionParams_ = null;
    private String taskId_ = null;
    private SExecutionManager sExecManager_ = null;

    public SExecutionTask(IStorlet storlet, OutputStream sOut,
            ArrayList<StorletInputStream> instreams,
            ArrayList<StorletOutputStream> outstreams,
            HashMap<String, String> executionParams,
            StorletLogger storletLogger, Logger logger,
            SExecutionManager sExecManager) {
        super(logger);
        this.storlet_ = storlet;
        this.sOut_ = sOut;
        this.inStreams_ = instreams;
        this.outStreams_ = outstreams;
        this.executionParams_ = executionParams;
        this.storletLogger_ = storletLogger;
        this.sExecManager_ = sExecManager;
    }

    public ArrayList<StorletInputStream> getInStreams() {
        return this.inStreams_;
    }

    public ArrayList<StorletOutputStream> getOutStreams() {
        return this.outStreams_;
    }

    public HashMap<String, String> getExecutionParams() {
        return this.executionParams_;
    }

    private void closeStorletInputStreams(){
        for(StorletInputStream stream : this.inStreams_){
            stream.close();
        }
    }

    private void closeStorletOutputStreams(){
        for(StorletOutputStream stream: this.outStreams_){
            stream.close();
        }
    }

    private void closeStorletStreams(){
        this.closeStorletInputStreams();
        this.closeStorletOutputStreams();
    }

    @Override
    public boolean exec() {
        boolean bStatus = true;
        this.taskId_ = this.sExecManager_.submitTask((SExecutionTask) this);
        return respond(this.sOut_, true, new String("OK"), this.taskId_);
    }

    @Override
    public void run() {
        try {
            this.storletLogger_.emitLog("About to invoke storlet");
            this.storlet_.invoke(inStreams_, outStreams_, executionParams_,
                    storletLogger_);
            this.storletLogger_.emitLog("Storlet invocation done");
            this.sExecManager_.cleanupTask(this.taskId_);
        } catch (StorletException e) {
            this.storletLogger_.emitLog(e.getMessage());
        } finally {
            this.storletLogger_.close();

            // We make sure all streams are closed
            this.closeStorletStreams();
        }
    }
}

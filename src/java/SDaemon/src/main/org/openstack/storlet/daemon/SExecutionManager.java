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

import java.io.OutputStream;
import java.io.IOException;

import java.util.HashMap;

import org.slf4j.LoggerFactory;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.Level;

import java.util.concurrent.*;

/*----------------------------------------------------------------------------
 * SExecutionManager
 *
 * This class manages tread workers to execute storlet application
 * */
public class SExecutionManager {

    private Logger logger_;
    private ExecutorService threadPool_;
    private String strStorletName_;
    private int nPoolSize;
    private HashMap<String, Future> taskIdToTask_;
    private static int nDefaultTimeoutToWaitBeforeShutdown_ = 3;

    public SExecutionManager(final String strStorletName,
            final Logger logger, final int nPoolSize) {
        this.strStorletName_ = strStorletName;
        this.logger_ = logger;
        this.nPoolSize = nPoolSize;
    }

    public void initialize() {
        this.logger_.trace("Initialising thread pool with "
            + nPoolSize + " threads");
        this.threadPool_ = Executors.newFixedThreadPool(nPoolSize);
        this.taskIdToTask_ = new HashMap<String, Future>();
    }

    public void terminate() {
        this.logger_.info(this.strStorletName_ + ": Shutting down threadpool");
        try {
            this.threadPool_.awaitTermination(
                    nDefaultTimeoutToWaitBeforeShutdown_,
                    TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        this.threadPool_.shutdown();
        this.logger_.info(this.strStorletName_ + ": threadpool down");
    }

    public String submitTask(final SExecutionTask sTask) {
        Future futureTask = threadPool_.submit(sTask);
        String taskId = futureTask.toString().split("@")[1];

        synchronized (this.taskIdToTask_) {
            this.taskIdToTask_.put(taskId, futureTask);
        }
        return taskId;
    }

    public boolean cancelTask(final String taskId) {
        boolean bStatus = true;
        if (this.taskIdToTask_.get(taskId) == null) {
            this.logger_.trace(this.strStorletName_ + ": " + taskId + " is not found");
            bStatus = false;
        } else {
            this.logger_.trace(this.strStorletName_ + ": cancelling " + taskId);
            (this.taskIdToTask_.get(taskId)).cancel(true);
            synchronized (this.taskIdToTask_) {
                this.taskIdToTask_.remove(taskId);
            }
        }
        return bStatus;
    }

    public void cleanupTask(final String taskId) {
        synchronized (this.taskIdToTask_) {
            this.taskIdToTask_.remove(taskId);
        }
    }
}

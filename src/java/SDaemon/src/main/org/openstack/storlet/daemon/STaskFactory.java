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

import java.io.FileOutputStream;
import java.io.FileDescriptor;
import java.io.OutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;

import org.slf4j.Logger;

import org.openstack.storlet.common.*;
import org.openstack.storlet.daemon.SExecutionTask;
import org.openstack.storlet.daemon.SExecutionManager;
import org.openstack.storlet.sbus.ServerSBusInDatagram;

/*----------------------------------------------------------------------------
 * StorletTaskFactory
 *
 * Analyze the request datagram. Setup the obtained file descriptors.
 * Prepare the storlet execution environment
 * */
public class STaskFactory {
    private IStorlet storlet_;
    private Logger logger_;

    public STaskFactory(IStorlet storlet, Logger logger) {
        this.storlet_ = storlet;
        this.logger_ = logger;
    }

    public SAbstractTask createStorletTask(
        ServerSBusInDatagram dtg, SExecutionManager sExecManager)
            throws StorletException {
        String command = dtg.getCommand();

        SAbstractTask ResObj = switch (command) {
            case "SBUS_CMD_HALT":
                this.logger_.trace("createStorletTask: received Halt command");
                yield createHaltTask(dtg);
            case "SBUS_CMD_EXECUTE":
                this.logger_.trace("createStorletTask: received Execute command");
                yield createExecutionTask(dtg, sExecManager);
            case "SBUS_CMD_PING":
                this.logger_.trace("createStorletTask: received Ping command");
                yield createPingTask(dtg);
            case "SBUS_CMD_CANCEL":
                this.logger_.trace("createStorletTask: received Cancel command");
                yield createCancelTask(dtg, sExecManager);
            default:
                this.logger_.error("createStorletTask: " + command
                    + " is not supported");
                yield null;
        };

        return ResObj;
    }

    private SExecutionTask createExecutionTask(
            ServerSBusInDatagram dtg, SExecutionManager sExecManager)
            throws StorletException {
        ArrayList<StorletInputStream> inStreams = new ArrayList<StorletInputStream>();
        ArrayList<StorletOutputStream> outStreams = new ArrayList<StorletOutputStream>();
        StorletLogger storletLogger = null;
        int nFiles = dtg.getNFiles();
        HashMap<String, HashMap<String, String>>[] FilesMD = dtg.getFilesMetadata();
        this.logger_.trace("StorletTask: Got " + nFiles + " fds");
        OutputStream sOut = null;
        for (int i = 0; i < nFiles; ++i) {
            HashMap<String, String> storletsMetadata = FilesMD[i].get("storlets");
            HashMap<String, String> storageMetadata = FilesMD[i].get("storage");
            FileDescriptor fd = dtg.getFiles()[i];

            String strFDtype = storletsMetadata.get("type");
            this.logger_.trace("createStorletTask: fd " + i + " is of type " + strFDtype);

            switch (strFDtype) {
                case "SBUS_FD_SERVICE_OUT":
                    sOut = new FileOutputStream(fd);
                    break;
                case "SBUS_FD_INPUT_OBJECT":
                    String start = storletsMetadata.get("start");
                    String end = storletsMetadata.get("end");
                    if (start != null && end != null) {
                        RangeStorletInputStream rangeStream;
                        try {
                            rangeStream = new RangeStorletInputStream(
                            fd,
                            storageMetadata,
                            Long.parseLong(start),
                            Long.parseLong(end));
                        } catch (IOException e) {
                            this.logger_.error("Got start="+start+" end="+end);
                            this.logger_.error(e.toString(), e);
                            throw new StorletException(e.toString());
                        }
                        inStreams.add((StorletInputStream)rangeStream);
                    } else {
                        inStreams.add(new StorletInputStream(fd, storageMetadata));
                    }
                    break;
                case "SBUS_FD_OUTPUT_OBJECT":
                    String strNextFDtype = dtg.getFilesMetadata()[i + 1]
                            .get("storlets").get("type");
                    if (!strNextFDtype.equals("SBUS_FD_OUTPUT_OBJECT_METADATA")) {
                        this.logger_.error("StorletTask: fd " + (i + 1)
                                + " is not SBUS_FD_OUTPUT_OBJECT_METADATA "
                                + " as expected");
                    } else {
                        this.logger_.trace("createStorletTask: fd " + (i + 1)
                                + " is of type SBUS_FD_OUTPUT_OBJECT_METADATA");
                    }
                    outStreams.add(new StorletObjectOutputStream(fd, storageMetadata,
                               dtg.getFiles()[i + 1]));
                    ++i;
                    break;
                case "SBUS_FD_LOGGER":
                    storletLogger = new StorletLogger(fd);
                    break;
                default:
                    this.logger_.error("createStorletTask: fd " + i
                            + " is of unknown type " + strFDtype);
            }
        }
        return new SExecutionTask(storlet_, sOut, inStreams, outStreams,
                dtg.getExecParams(), storletLogger, logger_, sExecManager);
    }

    private SCancelTask createCancelTask(
            ServerSBusInDatagram dtg, SExecutionManager sExecManager) {
        SCancelTask ResObj = null;
        String taskId = dtg.getTaskId();
        boolean bStatus = true;

        if (1 != dtg.getNFiles()) {
            this.logger_.error("createCancelTask: "
                    + "Wrong fd count for descriptor command. "
                    + "Expected 1, got " + dtg.getNFiles());
            bStatus = false;
        }
        this.logger_.trace("createCancelTask: #FDs is good");

        if (bStatus) {
            String strFDType = dtg.getFilesMetadata()[0].get("storlets").get("type");
            if (!strFDType.equals("SBUS_FD_SERVICE_OUT")) {
                this.logger_.error("createCancelTask: "
                        + "Wrong fd type for Cancel command. "
                        + "Expected SBUS_FD_SERVICE_OUT " + " got "
                        + strFDType);
                bStatus = false;
            }
            this.logger_.trace("createCancelTask: "
                    + "fd metadata is good. Creating stream");
        }

        if (bStatus) {
            OutputStream sOut = new FileOutputStream(dtg.getFiles()[0]);
            // parse descriptor stuff
            this.logger_.trace("createCancelTask: "
                    + "Returning StorletCancelTask");
            ResObj = new SCancelTask(sOut, logger_, sExecManager, taskId);
        }
        return ResObj;
    }

    private SHaltTask createHaltTask(ServerSBusInDatagram dtg) {
        SHaltTask ResObj = null;
        boolean bStatus = true;

        if (1 != dtg.getNFiles()) {
            this.logger_.error("createHaltTask: "
                    + "Wrong fd count for descriptor command. "
                    + "Expected 1, got " + dtg.getNFiles());
            bStatus = false;
        }
        this.logger_.trace("createHaltTask: #FDs is good");

        if (bStatus) {
            String strFDType = dtg.getFilesMetadata()[0].get("storlets").get("type");
            if (!strFDType.equals("SBUS_FD_SERVICE_OUT")) {
                this.logger_.error("createHaltTask: "
                        + "Wrong fd type for Halt command. "
                        + "Expected SBUS_FD_SERVICE_OUT " + " got "
                        + strFDType);
                bStatus = false;
            }
            this.logger_.trace("createHaltTask: "
                + "fd metadata is good. Creating object stream");
        }

        if (bStatus) {
            OutputStream sOut = new FileOutputStream(dtg.getFiles()[0]);
            // parse descriptor stuff
            this.logger_.trace("createHaltTask: " + "Returning StorletHaltTask");
            ResObj = new SHaltTask(sOut, logger_);
        }
        return ResObj;
    }

    private SPingTask createPingTask(ServerSBusInDatagram dtg) {
        SPingTask ResObj = null;
        boolean bStatus = true;

        if (1 != dtg.getNFiles()) {
            this.logger_.error("createPingTask: "
                    + "Wrong fd count for descriptor command. "
                    + "Expected 1, got " + dtg.getNFiles());
            bStatus = false;
        }
        this.logger_.trace("createPingTask: #FDs is good");

        if (bStatus) {
            String strFDType = dtg.getFilesMetadata()[0].get("storlets").get("type");
            if (!strFDType.equals("SBUS_FD_SERVICE_OUT")) {
                this.logger_.error("createPingTask: "
                        + "Wrong fd type for Ping command. "
                        + "Expected SBUS_FD_SERVICE_OUT " + " got "
                        + strFDType);
                bStatus = false;
            }
            this.logger_.trace("createPingTask: "
                    + "fd metadata is good. Creating object stream");
        }

        if (bStatus) {
            OutputStream sOut = new FileOutputStream(dtg.getFiles()[0]);
            // parse descriptor stuff
            this.logger_
                    .trace("createPingTask: " + "Returning StorletPingTask");
            ResObj = new SPingTask(sOut, logger_);
        }
        return ResObj;
    }
}

'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

'''
Created on Feb 10, 2015

@author: eranr
'''

import os
import time
import stat
import select
import commands

import eventlet
from eventlet.timeout import Timeout
import json
import shutil
import sys

from swift.common.constraints import MAX_META_OVERALL_SIZE 
from swift.common.swob import HTTPBadRequest, Request,\
    HTTPInternalServerError

from SBusPythonFacade.SBus import *
from SBusPythonFacade.SBusDatagram import *
from SBusPythonFacade.SBusStorletCommand import *
from SBusPythonFacade.SBusFileDescription import *
from storlet_middleware.storlet_common import StorletLogger

eventlet.monkey_patch()


'''---------------------------------------------------------------------------
Sandbox API
'''

class RunTimePaths():
    '''
    The Storlet Engine need to be access stuff located in many paths:
    1. The various communication channels represented as pipes in the filesystem
    2. Directories where to place Storlets
    3. Directories where to place logs
      
    Communication channels
    ----------------------
    The RunTimeSandbox communicates with the Sandbox via two types of pipes
    1. factory pipe - defined per account, used for communication with the sandbox
       for e.g. start/stop a storlet daemon
    2. Storlet pipe - defined per account and Storlet, used for communication
       with a storlet daemon, e.g. to call the invoke API
            
    Each pipe type has two paths:
    1. A path that is inside the sandbox
    2. A path that is outside of the sandbox or at the host side. As such
       this path is prefixed by 'host_'
        
    Thus, we have the following 4 paths of interest:
    1. sandbox_factory_pipe_path
    2. host_factory_pipe_path
    3. sandbox_storlet_pipe_path
    4. host_storlet_pipe_path

    Our implementation uses the following path structure for the various pipes:
    In the host, all pipes belonging to a given account are prefixed by 
    <pipes_dir>/<account>, where <pipes_dir> comes from the configuration
    Thus:
    host_factory_pipe_path is of the form <pipes_dir>/<account>/factory_pipe
    host_storlet_pipe_path is of the form <pipes_dir>/<account>/<storlet_id>

    In The sandbox side
    sandbox_factory_pipe_path is of the form /mnt/channels/factory_pipe
    sandbox_storlet_pipe_path is of the form  /mnt/channels/<storlet_id>

    Storlets Locations
    ------------------
    The Storlet binaries are accessible from the sandbox using a mounted directory.
    This directory is called the storlet directories.
    On the host side it is of the form <storlet_dir>/<account>/<storlet_name>
    On the sandbox side it is of the form /home/swift/<storlet_name>
    <storlet_dir> comes from the configuration
    <storlet_name> is the prefix of the jar.
    
    Logs
    ----
    Logs are located in paths of the form:
    <log_dir>/<account>/<storlet_name>.log
    '''
    def __init__(self, account, conf):
        self.account = account
        self.scope = account[5:18]
        self.host_restart_script_dir = conf['script_dir']
        self.host_pipe_root = conf['pipes_dir']
        self.factory_pipe_suffix = 'factory_pipe'
        self.sandbox_pipe_prefix = '/mnt/channels'
        self.storlet_pipe_suffix = '_storlet_pipe'
        self.sandbox_storlet_dir_prefix =  '/home/swift'
        self.host_storlet_root = conf['storlets_dir']
        self.host_log_path_root = conf['log_dir']
        self.host_cache_root = conf['cache_dir']
        self.storlet_container = conf['storlet_container']
        self.storlet_dependency = conf['storlet_dependency']


    def host_pipe_prefix(self):
        return os.path.join(self.host_pipe_root, self.scope)

    def create_host_pipe_prefix(self):
        path = self.host_pipe_prefix()
        if not os.path.exists(path):
            os.makedirs(path)
        # 0777 should be 0700 when we get user namespaces in Docker
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    def host_factory_pipe(self):
        return os.path.join(self.host_pipe_prefix(), 
                            self.factory_pipe_suffix)
    
    def host_storlet_pipe(self, storlet_id):
        return os.path.join(self.host_pipe_prefix(),
                            storlet_id)
    
    def sbox_storlet_pipe(self, storlet_id):
        return os.path.join(self.sandbox_pipe_prefix,
                            storlet_id)
        
    def sbox_storlet_exec(self, storlet_id):
        return os.path.join(self.sandbox_storlet_dir_prefix, storlet_id)
        
    def host_storlet_prefix(self):
        return os.path.join(self.host_storlet_root, self.scope)
    
    def host_storlet(self, storlet_id):
        return os.path.join(self.host_storlet_prefix(), storlet_id)
    
    def slog_path(self, storlet_id):
        log_dir = os.path.join(self.host_log_path_root, self.scope, storlet_id)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return log_dir
    
    def get_host_storlet_cache_dir(self):
        return os.path.join(self.host_cache_root, self.scope,self.storlet_container) 
                            
    def get_host_dependency_cache_dir(self):
        return os.path.join(self.host_cache_root, self.scope,self.storlet_dependency) 

'''---------------------------------------------------------------------------
Docker Stateful Container API
The RunTimeSandbox serve as an API between the Docker Gateway and 
a re-usable per account sandbox
---------------------------------------------------------------------------'''
class RunTimeSandbox():
    '''
    The RunTimeSandbox represents a re-usable per account sandbox. The sandbox
    is re-usable in the sense that it can run several storlet daemons.
     
    The following methods are supported:
    ping - pings the sandbox for liveness
    wait - wait for the sandbox to be ready for processing commands
    restart - restart the sandbox
    start_storlet_daemon - start a daemon for a given storlet
    stop_storlet_daemon - stop a daemon of a given storlet
    get_storlet_daemon_status - test if a given storlet daemon is running
    '''

    def __init__(self, account, conf, logger):
        self.paths = RunTimePaths(account, conf)
        self.account = account

        self.sandbox_ping_interval = 0.5
        self.sandbox_wait_timeout = int(conf['restart_linux_container_timeout'])

        self.docker_repo = conf['docker_repo']
        self.docker_image_name_prefix = 'tenant'

        # TODO: should come from upper layer Storlet metadata
        self.storlet_language = 'java'
        
        # TODO: add line in conf
        self.storlet_daemon_thread_pool_size = int(conf.get('storlet_daemon_thread_pool_size',5))
        self.storlet_daemon_debug_level = conf.get('storlet_daemon_debug_level','TRACE')
        
        # TODO: change logger's route if possible
        self.logger = logger
        
    
    def _parse_sandbox_factory_answer(self, str_answer):
        two_tokens = str_answer.split(':', 1)
        b_success = False
        if two_tokens[0] == 'True':
            b_success = True
        return b_success, two_tokens[1]

    def ping(self):
        pipe_path = self.paths.host_factory_pipe()
        
        read_fd, write_fd = os.pipe()
        dtg = SBusDatagram.create_service_datagram( SBUS_CMD_PING, write_fd )
        rc = SBus.send( pipe_path, dtg )
        if (rc < 0):
            return -1
        
        reply = os.read(read_fd,10)
        os.close(read_fd) 
        os.close(write_fd)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res == True:
            return 1
        return 0
                
    def wait(self):
        do_wait = True
        up = 0
        to = Timeout(self.sandbox_wait_timeout)
        try:
            while do_wait == True:
                rc = self.ping()
                if (rc != 1):
                    time.sleep(self.sandbox_ping_interval)
                    continue
                else:
                    to.cancel()
                    do_wait = False
                    up = 1
        except Timeout as t:
            self.logger.info("wait for sandbox %s timedout" % self.account)
            do_wait = False
        finally:
            to.cancel()

        return up
        
    def restart(self):
        '''
        Restarts the account's sandbox
        
        Returned value:
        True - If the sandbox was started successfully
        False - Otherwise

        '''
        # Extract the account's ID from the account
        if self.account.lower().startswith('auth_'):
            account_id = self.account[len('auth_'):]
        else:
            account_id = self.account
            
        self.paths.create_host_pipe_prefix()
        
        docker_container_name = '%s_%s' % (self.docker_image_name_prefix,
                                           account_id)    
        docker_image_name = '%s/%s' % (self.docker_repo,account_id)
        pipe_mount = '%s:%s' % (self.paths.host_pipe_prefix(), 
                                self.paths.sandbox_pipe_prefix)
        
        storlet_mount = '%s:%s' % (self.paths.host_storlet_prefix(), 
                                   self.paths.sandbox_storlet_dir_prefix)
        
        cmd = '%s/restart_docker_container %s %s %s %s' % ( 
                                        self.paths.host_restart_script_dir, 
                                        docker_container_name,
                                        docker_image_name, 
                                        pipe_mount, 
                                        storlet_mount)
        
        res = commands.getoutput(cmd) # YM python way of running a shell command. Runs a c program which invokes running dockerRun.  The middleware runs a user swift
        return self.wait()

    def start_storlet_daemon(self, spath, storlet_id):   ### YM this is step "3.5"
        prms = {}
        prms['daemon_language'] = 'java'
        prms['storlet_path']    = spath
        prms['storlet_name']    = storlet_id
        prms['uds_path']        = self.paths.sbox_storlet_pipe(storlet_id)
        prms['log_level']       = self.storlet_daemon_debug_level
        prms['pool_size']       = self.storlet_daemon_thread_pool_size
        
        read_fd, write_fd = os.pipe()
        dtg = SBusDatagram.create_service_datagram( SBUS_CMD_START_DAEMON, 
                                                    write_fd )
        dtg.set_exec_params( prms )
        
        pipe_path = self.paths.host_factory_pipe()
        rc = SBus.send( pipe_path, dtg )
        if (rc < 0):
            return -1
        reply = os.read(read_fd,10)
        os.close(read_fd) 
        os.close(write_fd)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res == True:
            return 1
        return 0
                
    def stop_storlet_daemon(self, storlet_id):
        read_fd, write_fd = os.pipe()
        dtg = SBusDatagram.create_service_datagram( SBUS_CMD_STOP_DAEMON, 
                                                    write_fd )
        dtg.add_exec_param('storlet_name', storlet_id)
        pipe_path = self.paths.host_factory_pipe()
        rc = SBus.send( pipe_path, dtg )
        if (rc < 0):
            self.logger.info("Failed to send status command to %s %s" % (self.account, storlet_id))
            return -1
        
        reply = os.read(read_fd,10)
        os.close(read_fd) 
        os.close(write_fd)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res == True:
            return 1
        return 0

    def get_storlet_daemon_status(self, storlet_id):
        read_fd, write_fd = os.pipe()
        dtg = SBusDatagram.create_service_datagram( SBUS_CMD_DAEMON_STATUS, 
                                                    write_fd )
        dtg.add_exec_param( 'storlet_name', storlet_id)
        pipe_path = self.paths.host_factory_pipe()
        rc = SBus.send(pipe_path, dtg)
        if (rc < 0):
            self.logger.info("Failed to send status command to %s %s" % (self.account, storlet_id))
            return -1
        reply = os.read(read_fd,10)
        os.close(read_fd) 
        os.close(write_fd)

        res, error_txt = self._parse_sandbox_factory_answer(reply)                             
        if res == True:
            return 1
        return 0

    def activate_storlet_daemon(self, invocation_data, cache_updated = True):
        storlet_daemon_status = self.get_storlet_daemon_status(invocation_data['storlet_main_class'])
        if (storlet_daemon_status == -1):
            # We failed to send a command to the factory.
            # Best we can do is execute the container.
            self.logger.debug('Failed to check Storlet daemon status, restart Docker container')
            res = self.restart()
            if (res != 1):
                raise Exception('Docker container is not responsive')
            storlet_daemon_status = 0
        
        if (cache_updated == True and storlet_daemon_status == 1):
            # The cache was updated while the daemon is running we need to stop it.
            self.logger.debug('The cache was updated, and the storlet daemon is running. Stopping daemon')
            res = self.stop_storlet_daemon( invocation_data['storlet_main_class'] )
            if res != 1:
                res = self.restart()
                if (res != 1):
                    raise Exception('Docker container is not responsive')
            else:
                self.logger.debug('Deamon stopped')
            storlet_daemon_status = 0
                 
        if (storlet_daemon_status == 0):
            self.logger.debug('Going to start storlet daemon!')
            class_path = '/home/swift/%s/%s' % (invocation_data['storlet_main_class'],
                                                invocation_data['storlet_name'])
            for dep in invocation_data['storlet_dependency'].split(','):
                class_path = '%s:/home/swift/%s/%s' %\
                            (class_path,
                             invocation_data['storlet_main_class'],
                             dep)
                            
            daemon_status = self.start_storlet_daemon(
                                class_path,
                                invocation_data['storlet_main_class'])

            if daemon_status != 1:
                self.logger.error('Daemon start Failed')
                raise Exception('Daemon start failed')
            else:
                self.logger.debug('Daemon started')

'''---------------------------------------------------------------------------
Storlet Daemon API
The StorletInvocationGETProtocol, StorletInvocationPUTProtocol
server as an API between the Docker Gateway and the Storlet Daemon which 
runs inside the Docker container. These classes implement the Storlet execution
protocol
---------------------------------------------------------------------------'''
class StorletInvocationProtocol():
                
    def _add_output_stream(self):
        self.fds.append(self.data_write_fd)
        md = dict()
        md['type'] = SBUS_FD_OUTPUT_OBJECT
        self.fdmd.append(md)

        self.fds.append(self.metadata_write_fd)
        md = dict()
        md['type'] = SBUS_FD_OUTPUT_OBJECT_METADATA
        self.fdmd.append(md)
        
    def _add_logger_stream(self):
        self.fds.append(self.storlet_logger.getfd())
        md = dict()
        md['type'] = SBUS_FD_LOGGER
        self.fdmd.append(md)
        
    def _prepare_invocation_descriptors(self):
        # Add the input stream
        self._add_input_stream()

        # Add the output stream        
        self.data_read_fd, self.data_write_fd = os.pipe()
        self.metadata_read_fd, self.metadata_write_fd = os.pipe()
        self._add_output_stream()
        
        # Add the logger
        self._add_logger_stream()
    
    def _close_remote_side_descriptors(self):
        if self.data_write_fd:
            os.close(self.data_write_fd)
        if self.metadata_write_fd:
            os.close(self.metadata_write_fd)
        
    def _invoke(self):
        dtg  = SBusDatagram()
        dtg.set_files( self.fds )
        dtg.set_metadata( self.fdmd )
        dtg.set_exec_params( self.srequest.params )
        dtg.set_command(SBUS_CMD_EXECUTE)
        rc = SBus.send( self.storlet_pipe_path, dtg )
        
        if (rc < 0):
            raise Exception("Failed to send execute command")

    def __init__(self, srequest, storlet_pipe_path, storlet_logger_path, timeout):
        self.srequest = srequest
        self.storlet_pipe_path = storlet_pipe_path
        self.storlet_logger_path = storlet_logger_path
        self.timeout = timeout
        
        # remote side file descriptors and their metadata lists
        # to be sent as part of invocation
        self.fds = list()
        self.fdmd = list()
        
        # local side file descriptors
        self.data_read_fd = None
        self.data_write_fd = None
        self.metadata_read_fd = None
        self.metadata_write_fd = None
        
        

        if not os.path.exists(storlet_logger_path):
            os.makedirs(storlet_logger_path)

    def _wait_for_read_with_timeout(self, fd):
        r, w, e = select.select([ fd ], [], [ ], self.timeout)
        if len(r) == 0:
            raise Timeout('Timeout while waiting for storlet output')
        if fd in r:
            return
        
    def _read_metadata(self):
        self._wait_for_read_with_timeout(self.metadata_read_fd)
        flat_json = os.read(self.metadata_read_fd, MAX_META_OVERALL_SIZE)
        if flat_json is not None:
            md = json.loads(flat_json)
        return md
                
class StorletInvocationGETProtocol(StorletInvocationProtocol):
    
    def _add_input_stream(self):
        self.fds.append(self.srequest.stream)
        # TODO: Break request metadata and systemmetadata
        md = dict()
        md['type'] = SBUS_FD_INPUT_OBJECT
        if self.srequest.user_metadata is not None:
            for key, val in self.srequest.user_metadata.iteritems():
                md[key] = val
        self.fdmd.append(md)

    def __init__(self, srequest, storlet_pipe_path, storlet_logger_path, timeout):
        StorletInvocationProtocol.__init__(self, srequest, storlet_pipe_path, storlet_logger_path, timeout)
    
    def communicate(self):            
        self.storlet_logger = StorletLogger(self.storlet_logger_path, 'storlet_invoke')
        self.storlet_logger.open()
        
        self._prepare_invocation_descriptors()
        try:
            self._invoke()
        except Exception as e:
            raise e
        finally:
            self._close_remote_side_descriptors()
            self.storlet_logger.close()
            
        out_md = self._read_metadata()
        os.close(self.metadata_read_fd)        
        self._wait_for_read_with_timeout(self.data_read_fd)
        
        return out_md, self.data_read_fd

    
class StorletInvocationPUTProtocol(StorletInvocationProtocol):
    
    def _add_input_stream(self):
        self.fds.append(self.input_data_read_fd)
        # TODO: Break request metadata and systemmetadata
        md = dict()
        md['type'] = SBUS_FD_INPUT_OBJECT
        if self.srequest.user_metadata is not None:
            for key, val in self.srequest.user_metadata.iteritems():
                md[key] = val
        self.fdmd.append(md)

    def __init__(self, srequest, storlet_pipe_path, storlet_logger_path, timeout):
        StorletInvocationProtocol.__init__(self, srequest, storlet_pipe_path, storlet_logger_path, timeout)
        self.input_data_read_fd, self.input_data_write_fd = os.pipe()
        # YM this pipe permits to take data from srequest.stream to input_data_write_fd
        # YM the write side stays with us, the read side is sent to storlet
        
    def _wait_for_write_with_timeout(self,fd):
        r, w, e = select.select([ ], [ fd ], [ ], self.timeout)
        if len(w) == 0:
            raise Timeout('Timeout while waiting for storlet to read')
        if fd in w:
            return
        
    def _write_with_timeout(self, writer, chunk):
        timeout = Timeout(self.timeout)
        try:
            writer.write(chunk)
        except Timeout as t:
            if t is timeout:
                writer.close()
                raise t
        except Exception as e:
            raise e
        finally:
            timeout.cancel()

    def _write_input_data(self):
        writer = os.fdopen(self.input_data_write_fd, 'w')
        reader = self.srequest.stream
        for chunk in iter(lambda: reader(65536), ''):
            self._write_with_timeout(writer, chunk)
        writer.close()

    def communicate(self):
        self.storlet_logger = StorletLogger(self.storlet_logger_path, 'storlet_invoke')
        self.storlet_logger.open()
        
        self._prepare_invocation_descriptors()
        try:
            self._invoke()
        except Exception as e:
            raise e
        finally:
            self._close_remote_side_descriptors()
            self.storlet_logger.close()
            
        self._wait_for_write_with_timeout(self.input_data_write_fd)
        # We do the writing in a different thread.
        # Otherwise, we can run into the following deadlock
        # 1. md writeds to Storlet
        # 2. Storlet reads and starts to write md and thed data
        # 3. md continues writing
        # 4. Storlet continues writing and gets stuck as md is busy writing,
        #    not consuming the reader end of the Storlet writer.
        eventlet.spawn_n(self._write_input_data)
        out_md = self._read_metadata()
        self._wait_for_read_with_timeout(self.data_read_fd)
        
        return out_md, self.data_read_fd

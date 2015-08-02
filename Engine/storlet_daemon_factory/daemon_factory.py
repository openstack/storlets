#!/usr/bin/python
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

'''===========================================================================
XX-XXX-2014    eranr      Initial implementation.
01-Sep-2014    evgenyl    Code refactoring.
01-Dec-2014    evgenyl    Dropping multi-threaded monitoring
==========================================================================='''

import os
import pwd
import sys
import time
import errno
import signal
import logging
import subprocess
from logging.handlers import SysLogHandler

from SBusPythonFacade.SBusStorletCommand import SBUS_CMD_START_DAEMON,\
    SBUS_CMD_STOP_DAEMON, SBUS_CMD_DAEMON_STATUS, SBUS_CMD_STOP_DAEMONS,\
    SBUS_CMD_PING, SBUS_CMD_HALT
from SBusPythonFacade.SBusFileDescription import SBUS_FD_OUTPUT_OBJECT
from SBusPythonFacade.SBus import SBus
from SBusPythonFacade.SBusDatagram import *

'''========================================================================'''


class daemon_factory():
    '''
    @summary: This class acts as the manager for storlet daemons.
              It listens to commands and reacts on them in an internal loop.
              As for now (01-Dec-2014) it is a single thread, synchronous
              processing.
    '''

    '''--------------------------------------------------------------------'''
    def __init__(self, path, logger):
        '''
        @summary:             CTOR
                              Prepare the auxiliary data structures

        @param path:          Path to the pipe file internal SBus listens to
        @type  path:          String
        @param logger:        Logger to dump the information to
        @type  logger:        SysLogHandler
        '''
        self.logger = logger
        self.pipe_path = path
        # Dictionary: map storlet name to pipe name
        self.storlet_name_to_pipe_name = dict()
        # Dictionary: map storlet name to daemon process PID
        self.storlet_name_to_pid = dict()
        
        self.NUM_OF_TRIES_PINGING_STARTING_DAEMON = 5

    '''--------------------------------------------------------------------'''
    def get_jvm_args(self,
                     daemon_language,
                     storlet_path,
                     storlet_name,
                     pool_size,
                     uds_path,
                     log_level,
                     container_id):
        '''
        @summary:               get_jvm_args
                                Check the input parameters, produce the list
                                of arguments for JVM process launch

        @param daemon_language: Language the storlet is written on.
                                Now (01-Dec-2014) only Java is supported.
        @type  daemon_language: String, 'java'
        @param storlet_path:    Path to the folder where storlet JRE file is
        @type  storlet_path:    String
        @param storlet_name:    Storlet main class name
        @type  storlet_name:    String
        @param pool_size:       Number of threads that storlet daemon's
                                thread pool provides
        @type  pool_size:       Integer
        @param uds_path:        Path to pipe daemon is going to listen to
        @type  uds_path:        String
        @param log_level:       Logger verbosity level
        @type  log_level:       String
        @param container_id:    container id
        @type  container_id:    String

        @return:                Error code, 0 if successful
        @rtype:                 Integer
        @return                 Error description
        @rtype:                 String
        @return:                A list of the JVM arguments
        @rtype:                 List
        '''

        str_library_path = "/opt/ibm"
        str_prfx = "/opt/ibm/"
        str_dmn_clspth = str_prfx + ':'
        str_dmn_clspth = str_dmn_clspth + str_prfx + \
            'logback-classic-1.1.2.jar:'
        str_dmn_clspth = str_dmn_clspth + str_prfx + 'logback-core-1.1.2.jar:'
        str_dmn_clspth = str_dmn_clspth + str_prfx + 'slf4j-api-1.7.7.jar:'
        str_dmn_clspth = str_dmn_clspth + str_prfx + 'json_simple-1.1.jar:'
        str_dmn_clspth = str_dmn_clspth + str_prfx + 'SBusJavaFacade.jar:'
        str_dmn_clspth = str_dmn_clspth + str_prfx + 'SCommon.jar:'
        str_dmn_clspth = str_dmn_clspth + str_prfx + 'SDaemon.jar:'

        str_dmn_clspth = str_dmn_clspth + storlet_path

        self.logger.debug('START_DAEMON: daemon lang = %s' % daemon_language)
        self.logger.debug('START_DAEMON: str_dmn_clspth = %s' % str_dmn_clspth)
        self.logger.debug('START_DAEMON: storlet_name = %s' % storlet_name)
        self.logger.debug('START_DAEMON: pool_size = %d' % pool_size)
        self.logger.debug('START_DAEMON: uds_path = %s' % uds_path)
        self.logger.debug('START_DAEMON: log_level = %s' % log_level)

        # We know the Daemon class and its dependencies
        str_daemon_main_class = "com.ibm.storlet.daemon.SDaemon"

        n_error_id = 0
        error_text = ''
        pargs = []
        if daemon_language == "java":
            self.logger.debug('START_DAEMON:preparing arguments')
            #Setting two environmental variables
            #The path strings are corrupted if passed is pargs list below
            os.environ['CLASSPATH'] = str_dmn_clspth
            os.environ['LD_LIBRARY_PATH'] = str_library_path
            pargs = [str('/usr/bin/java'),
                     str(str_daemon_main_class),
                     str(storlet_name),
                     str(uds_path),
                     str(log_level),
                     str('%d' % pool_size),
                     str(container_id)]
            str_pargs = ' '.join(map(str, pargs))
            self.logger.debug('START_DAEMON: pargs = %s' % str_pargs)
        else:
            n_error_id = -1
            error_text = "Got unsupported daemon language %s" % pargs
            self.logger.error(error_text)

        return n_error_id, error_text, pargs

    '''--------------------------------------------------------------------'''
    def spawn_subprocess(self, pargs):
        '''
        @summary:     spawn_subprocess
                      Launch a JVM process for some storlet daemon

        @param pargs: Arguments for the JVM
        @type  pargs: List of strings

        @return:      Status
        @rtype:       Boolean
        '''
        b_status = True
        error_text = ''
        try:
            self.logger.debug('START_DAEMON: actual invocation')
            self.logger.debug('The arguments are: {0}'.format(str(pargs)))
            dn = open('/dev/null', 'w')
            jvm_pid = subprocess.Popen(pargs,
                                       stdout=dn,
                                       stderr=dn,
                                       shell=False).pid
            # Wait for the JVM initializes itself
            time.sleep(1)
            self.logger.debug('JVM process ID is: {0}'.format(jvm_pid))
            storlet_name = pargs[2]

            # Does JVM run?
            b_status, error_text = self.get_process_status_by_pid(
                jvm_pid, storlet_name)
            if b_status:
                self.logger.debug('Keeping JVM PID in' +
                                  'storlet_name_to_pid[{0}] = {1}'.
                                  format(storlet_name, jvm_pid))
                # Keep JVM PID
                self.storlet_name_to_pid[storlet_name] = jvm_pid
                b_status, error_text = self.wait_for_daemon_to_initialize(
                                                              storlet_name)
                if not b_status:
                    raise 'No response from Daemon'
            self.logger.debug('START_DAEMON: just occurred')
            error_text = 'OK'
        except Exception as e:
            b_status = False
            error_text = 'Failed to start subprocess %s' % str(pargs)
            self.logger.error(error_text)
            self.logger.error('Exception is %s' % str(e))

        return b_status, error_text

    '''--------------------------------------------------------------------'''
    def wait_for_daemon_to_initialize(self, storlet_name):
        '''
        @summary:            wait_for_daemon_to_initialize
                             Send a Ping service datagram. Validate that
                             Daemon response is correct. Give up after the
                             predefined number of attempts (5)

        @param storlet_name: Storlet name we are checking the daemon for
        @type  storlet_name: String

        @return:             Status
        @rtype:              Boolean
        @return:             Description text of possible error
        @rtype:              String
        '''
        storlet_pipe_name = self.storlet_name_to_pipe_name[storlet_name] 
        self.logger.debug('Send PING command to {0} via {1}'.\
                          format(storlet_name,storlet_pipe_name))      
        read_fd, write_fd = os.pipe()
        dtg = SBusDatagram.create_service_datagram(SBUS_CMD_PING, write_fd)
        b_status = False
        error_text = "Daemon isn't responding"
        for i in range(self.NUM_OF_TRIES_PINGING_STARTING_DAEMON):
            ret = SBus.send(storlet_pipe_name, dtg)
            if (ret >= 0):
                resp = os.read(read_fd, 128)
                if 'OK' == resp:
                    b_status = True
                    error_text = 'OK'
                    break
            time.sleep(1)
        os.close(read_fd)
        os.close(write_fd)
        return b_status, error_text
        
    '''--------------------------------------------------------------------'''
    def process_start_daemon(self,
                             daemon_language,
                             storlet_path,
                             storlet_name,
                             pool_size,
                             uds_path,
                             log_level,
                             container_id):
        '''
        @summary: process_start_daemon
                  Start storlet daemon process

        @see:     get_jvm_args for the list of parameters

        @return:  Status
        @rtype:   Boolean

        '''
        # java -Djava.library.path=/root/workspace/nemo_storlet/bin
        # -Djava.class.path=/root/workspace/nemo_storlet/bin
        # com.ibm.storlet.daemon.StorletDaemon
        # storlet.test.TestStorlet
        # /tmp/aaa FINE 5

        b_status = True
        error_text = ''
        pargs = []
        n_error_id, error_text, pargs = self.get_jvm_args(daemon_language,
                                                          storlet_path,
                                                          storlet_name,
                                                          pool_size,
                                                          uds_path,
                                                          log_level,
                                                          container_id)
        if 0 != n_error_id:
            self.logger.debug('Problems with arguments for {0}'.
                              format(storlet_name))
            b_status = False

        if b_status:
            self.logger.debug('Assigning storlet_name_to_pipe_name[{0}]={1}'.
                              format(storlet_name, uds_path))
            self.storlet_name_to_pipe_name[storlet_name] = uds_path

        self.logger.debug('Validating that {0} is not already running'.
                          format(storlet_name))
        b_status, eror_text = self.get_process_status_by_name(storlet_name)
        if b_status:
            error_text = '{0} is already running'.format(storlet_name)
            self.logger.debug(error_text)
        else:
            error_text = '{0} is not running. About to spawn process'.\
                         format(storlet_name)
            self.logger.debug(error_text)
            b_status, error_text = self.spawn_subprocess(pargs)
            
        return b_status, error_text

    '''--------------------------------------------------------------------'''
    def get_process_status_by_name(self, storlet_name):
        '''
        @summary:            get_process_status_by_name
                             Check if the daemon runs for the specific storlet

        @param storlet_name: Storlet name we are checking the daemon for
        @type  storlet_name: String

        @return:             Status
        @rtype:              Boolean
        @return:             Description text of possible error
        @rtype:              String
        '''
        self.logger.debug('Current storlet name is: {0}'.format(storlet_name))
        self.logger.debug('storlet_name_to_pid has {0}'.
                          format(str(self.storlet_name_to_pid.keys())))
        b_status = False
        error_text = ''
        self.logger.debug('Checking status for storlet {0}'.
                          format(storlet_name))
        daemon_pid = self.storlet_name_to_pid.get(storlet_name, -1)
        if -1 != daemon_pid:
            b_status, error_text = self.get_process_status_by_pid(
                daemon_pid, storlet_name)
        else:
            error_text = 'Storlet name {0} not found in map'.\
                         format(storlet_name)
            self.logger.debug(error_text)

        return b_status, error_text

    '''--------------------------------------------------------------------'''
    def get_process_status_by_pid(self, daemon_pid, storlet_name):
        '''
        @summary:            get_process_status_by_pid
                             Check if a process with specific ID runs

        @param daemon_pid:   Storlet daemon process ID
        @type  daemon_pid:   Integer
        @param storlet_name: Storlet name we are checking the daemon for
        @type  storlet_name: String

        @return:             Status
        @rtype:              Boolean
        @return:             Description text of possible error
        @rtype:              String
        '''
        b_status = False
        error_text = ''
        obtained_pid = 0
        obtained_code = 0
        try:
            obtained_pid, obtained_code = os.waitpid(daemon_pid, os.WNOHANG)
            error_text = 'Storlet {0}, PID = {1}, ErrCode = {2}'.\
                         format(storlet_name, obtained_pid, obtained_code)
            self.logger.debug(error_text)
        except OSError, err:
            if err.errno == errno.ESRCH:
                error_text = 'No running daemon for {0}'.format(storlet_name)
            elif err.errno == errno.EPERM:
                error_text = 'No permission to access daemon for {0}'.\
                    format(storlet_name)
            else:
                error_text = 'Unknown error'
        else:
            if 0 == obtained_pid and 0 == obtained_code:
                error_text = 'Storlet {0} seems to be OK'.format(storlet_name)
                b_status = True
            else:
                error_text = 'Storlet {0} is terminated'.format(storlet_name)
            self.logger.debug(error_text)
        return b_status, error_text

    '''--------------------------------------------------------------------'''
    def process_kill(self, storlet_name):
        '''
        @summary:            process_kill
                             Kill the storlet daemon immediately
                             (kill -9 $DMN_PID)

        @param storlet_name: Storlet name we are checking the daemon for
        @type  storlet_name: String

        @return:             Status
        @rtype:              Boolean
        @return:             Description text of possible error
        @rtype:              String
        '''
        self.logger.debug('Current storlet name is: {0}'.format(storlet_name))
        b_success = True
        error_text = ''
        dmn_pid = self.storlet_name_to_pid.get(storlet_name, -1)
        self.logger.debug('Daemon PID is: {0}'.format(dmn_pid))
        if -1 != dmn_pid:
            try:
                os.kill(dmn_pid, signal.SIGKILL)
                obtained_pid, obtained_code = os.waitpid(dmn_pid, os.WNOHANG)
                error_text = 'Storlet {0}, PID = {1}, ErrCode = {2}'.\
                             format(storlet_name, obtained_pid, obtained_code)
                self.logger.debug(error_text)
            except:
                self.logger.debug('Crash while killing storlet')
            self.storlet_name_to_pid.pop(storlet_name)
        else:
            error_text = '{0} is not found'.format(storlet_name)
            b_success = False

        return b_success, error_text

    '''--------------------------------------------------------------------'''
    def process_kill_all(self):
        '''
        @summary: process_kill_all
                  Iterate through storlet daemons. Kill every one.

        @return:  Status (True)
        @rtype:   Boolean
        @return:  Description text of possible error ('OK')
        @rtype:   String
        '''
        for storlet_name in self.storlet_name_to_pid.keys():
            self.process_kill(storlet_name)
        return True, 'OK'

    '''--------------------------------------------------------------------'''
    def shutdown_all_processes(self):
        '''
        @summary: shutdown_all_processes
                  send HALT command to every spawned process
        '''
        answer = ''
        for storlet_name in self.storlet_name_to_pid.keys():
            self.shutdown_process(storlet_name)
            answer += storlet_name + ': terminated; '
        self.logger.info('All the processes terminated')
        self.logger.info(answer)
        return True, answer

    '''--------------------------------------------------------------------'''
    def shutdown_process(self, storlet_name):
        '''
        @summary:            send HALT command to storlet daemon

        @param storlet_name: Storlet name we are checking the daemon for
        @type  storlet_name: String

        @return:             Status
        @rtype:              Boolean
        @return:             Description text of possible error
        @rtype:              String
       '''
        b_status = False
        error_text = ''
        self.logger.debug('Inside shutdown_process {0}'.format(storlet_name)) 
        storlet_pipe_name = self.storlet_name_to_pipe_name[storlet_name] 
        self.logger.debug('Send HALT command to {0} via {1}'.\
                          format(storlet_name,storlet_pipe_name))      
        read_fd, write_fd = os.pipe()
        dtg = SBusDatagram.create_service_datagram(SBUS_CMD_HALT, write_fd)
        SBus.send(storlet_pipe_name, dtg)
        os.close(read_fd)
        os.close(write_fd)
        dmn_pid = self.storlet_name_to_pid.get(storlet_name, -1)
        self.logger.debug('Storlet Daemon PID is {0}'.\
                          format(dmn_pid))      
        if -1 != dmn_pid:
            os.waitpid(dmn_pid,0)
            self.storlet_name_to_pid.pop(storlet_name)
            b_status = True
        return b_status
    
    '''--------------------------------------------------------------------'''
    def dispatch_command(self, dtg, container_id):
        '''
        @summary:   dispatch_command
                    Parse datagram. React on the request.  

        @param dtg: Datagram to process
        @type  dtg: SBus python facade Datagram
        @param container_id: container id
        @type  container_id: String
        
        @return:    Status
        @rtype:     Boolean
        @return:    Description text of possible error
        @rtype:     String
        @return:    Flag - whether we need to continue operating
        @rtype:     Boolean  
       '''
        b_status = False
        error_text = ''
        b_iterate = True
        command = -1
        try:
            command = dtg.get_command()
        except Exception:
            error_text = "Received message does not have command"\
                         " identifier. continuing."
            b_status = False
            self.logger.error( error_text )
        else:
            self.logger.debug("Received command {0}".format(command))
                        
        prms = dtg.get_exec_params()
        if command == SBUS_CMD_START_DAEMON:
            self.logger.debug( 'Do SBUS_CMD_START_DAEMON' )
            self.logger.debug( 'prms = %s'%str(prms) )
            b_status, error_text = \
                self.process_start_daemon(prms['daemon_language'],
                                          prms['storlet_path'], 
                                          prms['storlet_name'], 
                                          prms['pool_size'], 
                                          prms['uds_path'], 
                                          prms['log_level'],
                                          container_id)
        elif command == SBUS_CMD_STOP_DAEMON:
            self.logger.debug( 'Do SBUS_CMD_STOP_DAEMON' )
            b_status, error_text = self.process_kill(\
                                                prms['storlet_name'])
        elif command == SBUS_CMD_DAEMON_STATUS:
            self.logger.debug( 'Do SBUS_CMD_DAEMON_STATUS' )
            b_status, error_text = self.get_process_status_by_name(\
                                                         prms['storlet_name'])
        elif command == SBUS_CMD_STOP_DAEMONS:
            self.logger.debug( 'Do SBUS_CMD_STOP_DAEMONS' )
            b_status, error_text = self.process_kill_all()
            b_iterate = False
        elif command == SBUS_CMD_HALT:
            self.logger.debug( 'Do SBUS_CMD_HALT' )
            b_status, error_text = self.shutdown_all_processes()
            b_iterate = False
        elif command == SBUS_CMD_PING:
            self.logger.debug( 'Do SBUS_CMD_PING' )
            b_status = True
            error_text = 'OK'
        else:
            b_status = False
            error_text = "got unknown command %d" % command
            self.logger.error( error_text )
        
        self.logger.debug( 'Done' )
        return b_status, error_text, b_iterate
        
    '''--------------------------------------------------------------------'''
    def main_loop(self, container_id):
        '''
        @summary: main_loop
                  The 'internal' loop. Listen to SBus, receive datagram,
                  dispatch command, report back.
        '''
        # Create SBus. Listen and process requests
        sbus = SBus()
        fd = sbus.create( self.pipe_path )
        if fd < 0:
            self.logger.error("Failed to create SBus. exiting.")
            return
    
        b_iterate = True
        b_status = True
        error_text = ''
        
        while b_iterate:
            rc = sbus.listen(fd)
            if rc < 0:
                self.logger.error("Failed to wait on SBus. exiting.")
                return
            self.logger.debug("Wait returned")
        
            dtg = sbus.receive(fd)
            if not dtg:
                self.logger.error("Failed to receive message. exiting.")
                return
        
            try:
                outfd = dtg.get_first_file_of_type( SBUS_FD_OUTPUT_OBJECT )
            except Exception:
                self.logger.error("Received message does not have outfd."\
                                  " continuing.")
                continue
            else:
                self.logger.debug("Received outfd %d" % outfd.fileno())

            b_status, error_text, b_iterate = self.dispatch_command(dtg, container_id)
                
            self.log_and_report(outfd, b_status, error_text)
            outfd.close()
            
        # We left the main loop for some reason. Terminating.
        self.logger.debug( 'Leaving main loop' )
        
    '''--------------------------------------------------------------------'''
    def log_and_report(self, outfd, b_status, error_text):
        '''
        @summary:          log_and_report
                           Send the result description message 
                           back to swift middlewear
                           
        @param outfd:      Output channel to send the message to
        @type  outfd:      File descriptor
        @param b_status:   Flag, whether the operation was successful
        @type:             Boolean
        @param error_text: The result description
        @type error_text:  String
         
        @rtype:            void
        '''
        num = -1;
        answer = str(b_status) + ': ' + error_text
        self.logger.debug(' Just processed command')
        self.logger.debug(' Going to answer: %s'%answer)
        try:
            num = outfd.write( answer )
            self.logger.debug(" ... and still alive")
        except:
            self.logger.debug('Problem while writing response %s'%answer)

'''======================= END OF daemon_factory CLASS ===================='''

'''------------------------------------------------------------------------'''
def start_logger(logger_name, log_level, container_id):
    '''
    @summary:           start_logger
                        Initialize logging of this process. 
                        Set the logger format.
                        
    @param logger_name: The name to report with
    @type  logger_name: String
    @param log_level:   The verbosity level
    @type  log_level:   String
    
    @rtype:             void 
    '''
    logging.raiseExceptions = False
    log_level = log_level.upper()

    if (log_level == 'DEBUG'):
        level = logging.DEBUG
    elif (log_level == 'INFO'):
        level = logging.INFO
    elif (log_level == 'WARNING'):
        level = logging.WARN
    elif (log_level == 'CRITICAL'):
        level = logging.CRITICAL
    else:
        level = logging.ERROR


    logger = logging.getLogger("CONT #" + container_id + ": " + logger_name)

    if log_level == 'OFF':
        logging.disable(logging.CRITICAL)
    else:
        logger.setLevel(level)
    
    for i in range(0,4):
        try:
            sysLogh = SysLogHandler('/dev/log')
            break
        except Exception as e:
            if i<3:
                time.sleep(1)
            else:
                raise e
            
    str_format = '%(name)-12s: %(levelname)-8s %(funcName)s'+\
                 ' %(lineno)s [%(process)d, %(threadName)s]'+\
                 ' %(message)s'
    formatter = logging.Formatter(str_format)
    sysLogh.setFormatter(formatter)
    sysLogh.setLevel(level)
    logger.addHandler(sysLogh)
    return logger

'''------------------------------------------------------------------------'''
def usage():
    '''
    @summary: usage
              Print the expected command line arguments.
               
    @rtype:   void
    '''
    print "daemon_factory <path> <log level> <container_id>"

'''------------------------------------------------------------------------'''
def main(argv):
    '''
    @summary: main
              The entry point. 
              - Initialize logger, 
              - impersonate to swift user,
              - create an instance of daemon_factory, 
              - start the main loop. 
    '''
    if (len(argv) != 3):
        usage()
        return
    
    pipe_path = argv[0]
    log_level = argv[1]
    container_id = argv[2]
    logger = start_logger("daemon_factory", log_level, container_id)
    logger.debug("Daemon factory started")
    SBus.start_logger("DEBUG", container_id=container_id)
        
    # Impersonate the swift user
    pw = pwd.getpwnam('swift')
    os.setresgid(pw.pw_gid,pw.pw_gid,pw.pw_gid)
    os.setresuid(pw.pw_uid,pw.pw_uid,pw.pw_uid)

    
    factory = daemon_factory(pipe_path, logger)
    factory.main_loop(container_id)

'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main(sys.argv[1:])

'''============================ END OF FILE ==============================='''

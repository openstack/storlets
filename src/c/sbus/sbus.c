/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
 * Copyright (c) 2010-2016 OpenStack Foundation
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
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <syslog.h>
#include <stdlib.h>
#include <sys/un.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#include <stdarg.h>


#include "sbus.h"

#define SBUS_SYSLOG_PATH  "sbus"
#define MAX_FDS           4096
#define MAX_MSG_LENGTH    4096


/*----------------------------------------------------------------------------
 * translate_log_level
 *
 * auxiliary function, converts string to a predefined constant
 * recognized by syslog
 *
 */
static
int sbus_translate_log_level( const char* str_log_level )
{
    int level;
    if( strncmp(      str_log_level, "DEBUG",    5 ) == 0 )
        level = LOG_DEBUG;
    else if( strncmp( str_log_level, "INFO",     4 ) == 0 )
        level = LOG_INFO;
    else if( strncmp( str_log_level, "WARNING",  7 ) == 0 )
        level = LOG_WARNING;
    else if( strncmp( str_log_level, "CRITICAL", 8 ) == 0 )
        level = LOG_CRIT;
    else if( strncmp( str_log_level, "OFF",      3 ) == 0 )
        level = LOG_EMERG;
    else
        level = LOG_ERR;

    return level;
}

char str[80] = "CONT #";

void sbus_start_logger( const char* str_log_level, const char* container_id )
{
    int n_level = sbus_translate_log_level( str_log_level );

    closelog();

    strcat(str, container_id);
    strcat(str, ": ");
    strcat(str, SBUS_SYSLOG_PATH);

    openlog( str, LOG_PID, LOG_SYSLOG );
    if( LOG_EMERG == n_level )
        setlogmask( LOG_EMERG );
    else
        setlogmask( LOG_UPTO( n_level ) );
    syslog( LOG_ERR,
            "sbus_start_logger: Started with Level  %s",
            str_log_level );
}

void sbus_stop_logger( void )
{
    closelog();
}

int sbus_create( const char* str_sbus_path )
{
    int n_status = 0;
    int n_sbus_handle = socket( PF_UNIX, SOCK_DGRAM, 0 );
    if( n_sbus_handle < 0 )
    {
        syslog( LOG_ERR,
                "sbus_create: Failed to create a socket. %s",
                strerror( errno ) );
        n_status = -1;
    }

    if( 0 <= n_status )
    {
        struct sockaddr_un sockaddr;
        memset( &sockaddr, 0, sizeof(sockaddr) );
        sockaddr.sun_family = AF_UNIX;
        strncpy( sockaddr.sun_path,
                 str_sbus_path,
                 sizeof( sockaddr.sun_path ) );
        sockaddr.sun_path[sizeof(sockaddr.sun_path)-1] = 0;
        unlink( sockaddr.sun_path ); //TBD - How to handle it

        n_status = bind( n_sbus_handle,
                         (struct sockaddr *) &sockaddr,
                         sizeof(sockaddr) );
        if( -1 == n_status )
        {
            syslog( LOG_ERR,
                   "sbus_create: Failed to bind to socket. %s",
                   strerror(errno) );
            close(n_sbus_handle);
        }

        char mode[] = "0777";
        n_status = chmod( str_sbus_path, strtol(mode, 0, 8) );
        if( 0 != n_status )
        {
            syslog( LOG_ERR,
                    "sbus_create: Failed to set socket permissions. %s",
                    strerror(errno) );
            close(n_sbus_handle);
        }

        int nReuse = 1;
        n_status = setsockopt( n_sbus_handle,
                               SOL_SOCKET,
                               SO_REUSEADDR,
                               &nReuse,
                               sizeof(nReuse) );
        if( -1 == n_status )
        {
            syslog( LOG_ERR,
                    "sbus_create: Failed to set socket options. %s",
                    strerror(errno));
                    close( n_sbus_handle );
        }
    }
    syslog( LOG_DEBUG,
            "sbus_create: SBus created at - %s", str_sbus_path );

    return ( 0 <= n_status ? n_sbus_handle : n_status );
}

int sbus_listen( int n_sbus_handle )
{
    fd_set fdset;

    FD_ZERO( &fdset );
    FD_SET( n_sbus_handle, &fdset );

    int n_status = select( n_sbus_handle+1,
                           &fdset,
                           (fd_set *)0,
                           (fd_set *)0,
                           (struct timeval*) 0);
    if( 0 > n_status )
        syslog( LOG_ERR,
                "sbus_listen: Select returned unexpectedly. %s",
                strerror(errno));
    else
    {
        if( !FD_ISSET( n_sbus_handle, &fdset ) )
        {
            // TBD +1 means return to select.
            syslog( LOG_ERR,
                    "sbus_listen: Select returned on a different fs. %s",
                    strerror(errno) );
                    n_status = 1;
        }
        else
            n_status = 0;
    }
    syslog( LOG_DEBUG,
            "sbus_listen: SBus listened successfully" );

    return n_status;
}


/*=========================== MESSAGE SENDING ==============================*/

/*----------------------------------------------------------------------------
 * dump_data_to_bytestream
 *
 * auxiliary string processing, collects provided data to a single byte stream
 * The "protocol" is : 3 integers, 2 strings
 */
static
int dump_data_to_bytestream( char** pp_bytestream,
                             int n_files,
                             const char* str_files_metadata,
                             int n_files_metadata_len,
                             const char* str_msg_data,
                             int n_msg_len )
{
    int int_size = sizeof( int );

    int n_status = 0;
    // The byte stream length is computed as the sum of
    // 2 char-encoded buffers;
    // 3 integers: number of files, lengths of metadata and message;
    // terminating NULL
    int n_bytestream_len = n_files_metadata_len + n_msg_len + 3 * int_size + 1;
    *pp_bytestream = (char*)(malloc)(n_bytestream_len);
    if( NULL == *pp_bytestream ) {
        syslog( LOG_ERR,
                "dump_data_to_bytestream: "
                "unable to allocate %d bytes of memory, error = %s",
                n_bytestream_len,
                strerror(errno) );
        n_status = -1;
    }
    if( 0 == n_status ) {
        int n_offset = 0;
        memcpy( *pp_bytestream + n_offset, (void*) &n_files, int_size );
        n_offset += int_size;
        memcpy( *pp_bytestream + n_offset, (void*) &n_files_metadata_len,
                int_size );
        n_offset += int_size;
        memcpy( *pp_bytestream + n_offset, (void*) &n_msg_len, int_size );
        n_offset += int_size;
    memcpy( *pp_bytestream + n_offset, (void*) str_files_metadata,
                n_files_metadata_len );
        n_offset += n_files_metadata_len;
        memcpy( *pp_bytestream + n_offset, (void*) str_msg_data, n_msg_len );
    }
    return ( 0 == n_status ? n_bytestream_len : -1 );
}

/*----------------------------------------------------------------------------
 * sbus_pack_message
 * prepares msghdr structure to be sent, fills it with the actual data
 */
static
int sbus_pack_message( struct msghdr* p_message,
                       struct iovec* p_msg_iov,
                       const int* p_files,
                       int n_files,
                       const char* str_files_metadata,
                       int n_files_metadata_len,
                       const char* str_msg_data,
                       int n_msg_len )
{
    int n_status = 0;
    syslog( LOG_DEBUG, "sbus_pack_message: Got message with %d files",
            n_files );

    char* p_bytestream = NULL;
    int n_bytestream_len = dump_data_to_bytestream( &p_bytestream,
                                                    n_files,
                                                    str_files_metadata,
                                                    n_files_metadata_len,
                                                    str_msg_data,
                                                    n_msg_len );
    if( n_bytestream_len > 0 ) {
        int n_files_block_len = n_files * sizeof(int);
        int n_cbuf_size = CMSG_LEN( n_files_block_len );
        char* cmsg_buf = (char*)(malloc)(n_cbuf_size);
        p_msg_iov->iov_base = p_bytestream;
        p_msg_iov->iov_len = n_bytestream_len;
        p_message->msg_iov = p_msg_iov;
        p_message->msg_iovlen = 1;
        p_message->msg_control = cmsg_buf;
        p_message->msg_controllen = n_cbuf_size;

        struct cmsghdr* cmsg = CMSG_FIRSTHDR(p_message);
        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = p_message->msg_controllen;
        memcpy(CMSG_DATA(cmsg), (void*) p_files, n_files * sizeof(int));
    } else
        n_status = -1;

    return n_status;
}

/*----------------------------------------------------------------------------
 * sbus_send_msg
 * packs the message data and sends it
 */
int sbus_send_msg( const char* str_sbus_path,
                   const int* p_files,
                   int n_files,
                   const char* str_files_metadata,
                   int n_files_metadata_len,
                   const char* str_msg_data,
                   int n_msg_len  )
{
    int n_sock = socket(PF_UNIX, SOCK_DGRAM, 0);
    if( 0 > n_sock ) {
        syslog( LOG_ERR,
                "sbus_send_msg: Failed to create socket. %s",
                strerror(errno));
                return -1;
    }

    /* Some network stuff */
    struct sockaddr_un sockaddr;
    memset( &sockaddr, 0, sizeof(sockaddr) );
    sockaddr.sun_family = AF_UNIX;
    strncpy(sockaddr.sun_path, str_sbus_path, sizeof(sockaddr.sun_path));
    sockaddr.sun_path[sizeof(sockaddr.sun_path)-1]=0;
    struct msghdr the_message;
    memset(&the_message, 0, sizeof(the_message));
    the_message.msg_name = &sockaddr;
    the_message.msg_namelen = sizeof(sockaddr);
    struct iovec msg_iov;

    int n_status = 0;
    n_status = sbus_pack_message( &the_message,
                                  &msg_iov,
                                  p_files,
                                  n_files,
                                  str_files_metadata,
                                  n_files_metadata_len,
                                  str_msg_data,
                                  n_msg_len );

    if( 0 > n_status ) {
        close( n_sock );
    } else {
        // Send message to factory daemon via the socket.
        n_status = sendmsg( n_sock, &the_message, 0 );
        if( 0 > n_status )
            syslog( LOG_ERR,
                    "sbus_send_msg: Failed to send message on channel %s,"
                    " error is %s. Is server side running?",
                    str_sbus_path, strerror(errno) );

        // Free resources.
        free( the_message.msg_iov->iov_base );
        if( NULL != the_message.msg_control )
            free(the_message.msg_control);
        close(n_sock);
    }
    if( 0 <= n_status )
        syslog( LOG_DEBUG,
                "sbus_send_msg: Message with %d files was sent through %s",
                n_files, str_sbus_path );
    return n_status;
}


/*=========================== MESSAGE RECEIVING ============================*/

/*----------------------------------------------------------------------------
 * sbus_extract_integer
 * reads sizeof(int) from character stream and packs an integer.
 * Assumption: the stream is expected to be at least sizeof(int) long
 */
static
int sbus_extract_integer( const char* p_str )
{
    int n_res = 0;
    memcpy( (void*) &n_res, p_str, sizeof(int) );
    return n_res;
}

/*----------------------------------------------------------------------------
 * sbus_copy_substr
 * allocates a new buffer of n_len characters,
 * copies n_len characters from p_src to the new buffer
 * Caller shall free the allocated chunk.
 */
static
char* sbus_copy_substr( const char* p_src,
                        int n_len )
{
    char* p_dst = (char*) malloc( n_len + 1 );
    memset( p_dst, 0, n_len + 1 );
    memcpy( p_dst, p_src, n_len );
    return p_dst;
}

/*----------------------------------------------------------------------------
 * sbus_extract_files
 * allocates a new buffer of n_files file descriptors,
 * Caller shall free the allocated chunk.
 */
static
int sbus_extract_files( struct msghdr* p_msg,
                        int n_files,
                        int** pp_files )
{
    int n_status = 0;
    struct cmsghdr* cmsg = CMSG_FIRSTHDR(p_msg);
    if( NULL == cmsg ) {
        syslog( LOG_ERR,
                "sbus_extract_files: NULL cmsg. Error is %s",
                strerror(errno) );
        n_status = -1;
    }

    if( 0 != n_status || SCM_RIGHTS != cmsg->cmsg_type ) {
        syslog( LOG_ERR,
                "sbus_extract_files: cmsg with wrong type. Type is %d",
                cmsg->cmsg_type );
        n_status = -1;
    }

    if( 0 != n_status || SOL_SOCKET != cmsg->cmsg_level ) {
        syslog( LOG_ERR,
                "sbus_extract_files: cmsg with wrong level. Level is %d",
                cmsg->cmsg_level );
        n_status = -1;
    }

    int n_actual_num = ( cmsg->cmsg_len - CMSG_LEN(0) ) / sizeof(int);
    if( 0 != n_status || n_actual_num != n_files ) {
        syslog( LOG_ERR,
                "sbus_extract_files:  Incompatible number of descriptors"
                " in message. expected %d, found %d",
                n_files, n_actual_num );
        n_status = -1;
    }

    int i;
    *pp_files = (int*) malloc( n_files * sizeof(int) );
    for( i = 0; i < n_files; ++i ) {
        (*pp_files)[i] = ( (int*) CMSG_DATA( cmsg ) )[i];
    }
    return n_status;
}
/*----------------------------------------------------------------------------
 * sbus_recv_msg
 * receives the data and unpacks the message
 */
int sbus_recv_msg( int n_sbus_handler,
                   int** pp_files,
                   int* pn_files,
                   char** pstr_files_metadata,
                   int* pn_files_metadata_len,
                   char** pstr_msg_data,
                   int* pn_msg_len ) {

    int n_status = 0;
    char str_msg_buf[MAX_MSG_LENGTH];
    char cmsg_buf[ CMSG_SPACE( MAX_FDS * sizeof(int) ) ];
    char str_name[128];
    struct iovec msg_iov;

    msg_iov.iov_base = &str_msg_buf;
    msg_iov.iov_len  = sizeof(str_msg_buf);

    struct msghdr recv_msg;
    memset( &recv_msg, 0, sizeof(recv_msg) );
    recv_msg.msg_iov = &msg_iov;
    recv_msg.msg_iovlen = 1;
    recv_msg.msg_control = cmsg_buf;
    recv_msg.msg_controllen = sizeof(cmsg_buf);
    recv_msg.msg_name = str_name;
    recv_msg.msg_namelen = sizeof(str_name );

    int n_msg_len = recvmsg( n_sbus_handler, &recv_msg, 0 );
    if( n_msg_len < 0 ) {
        syslog(LOG_ERR, "sbus_recv_msg: recvmsg failed. %s", strerror(errno));
    close(n_sbus_handler);
    n_status = -1;
    }

    if( 0 <= n_status ) {
        int int_size = sizeof(int);
        int* n_lengths[3] = {pn_files, pn_files_metadata_len, pn_msg_len};
        char* p_bytestream = recv_msg.msg_iov->iov_base;
        int i;
        for( i = 0; i < 3; ++i )
            *(n_lengths[i]) = sbus_extract_integer(p_bytestream + i*int_size);

        if( 0 < *pn_files )
            sbus_extract_files( &recv_msg, *pn_files , pp_files );

        int n_offset = 3 * int_size;
        if( 0 < *pn_files_metadata_len )
            *pstr_files_metadata = sbus_copy_substr( p_bytestream + n_offset,
                                                     *pn_files_metadata_len );

        n_offset += *pn_files_metadata_len;
        if( 0 < *pn_msg_len )
            *pstr_msg_data = sbus_copy_substr( p_bytestream + n_offset, *pn_msg_len );

    }
    if( 0 <= n_status )
        syslog( LOG_DEBUG,
                "sbus_recv_msg: Message with %d files was received",
                *pn_files );

    return n_status;
}

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

#include <jni.h>
#include <stdlib.h>
#include <stdio.h>
#include <syslog.h>
#include <string.h>

#include "org_openstack_storlet_sbus_SBusJNI.h"
#include "sbus.h"


static int  g_JavaAccessorsInitialized = 0;


static jclass       g_ClassRawMessage       = NULL;
static jmethodID    g_RawMessageCTOR        = NULL;
static jfieldID     g_FieldFDs              = NULL;
static jfieldID     g_FieldMetadata         = NULL;
static jfieldID     g_FieldParams           = NULL;

static jclass       g_ClassFileDescriptor   = NULL;
static jmethodID    g_FDCTOR                = NULL;
static jfieldID     g_FieldRawFD            = NULL;

/*----------------------------------------------------------------------------
 * init_java_accessors
 *
 * Preparing access to some Java-land objects
 * */
int init_java_accessors( JNIEnv* env )
{
    // TODO: Fix to read only once.
    // Currently seem to fail
    //if( 1 == g_JavaAccessorsInitialized )
    //    return 0;

    /*------------------------------------------------------------------------
     * Reflecting SBusRawMessage
     * */
    g_ClassRawMessage =
            (*env)->FindClass( env, "org/openstack/storlet/sbus/SBusRawMessage" );
    if( NULL == g_ClassRawMessage )
        return -1;

    g_RawMessageCTOR =
            (*env)->GetMethodID(env, g_ClassRawMessage, "<init>", "()V");
    if( NULL == g_RawMessageCTOR )
        return -1;

    g_FieldFDs =
            (*env)->GetFieldID( env, g_ClassRawMessage,
                                "hFiles_", "[Ljava/io/FileDescriptor;");
    if( NULL == g_FieldFDs )
        return -1;

    g_FieldParams =
            (*env)->GetFieldID( env, g_ClassRawMessage,
                                "strParams_", "Ljava/lang/String;");
    if( NULL == g_FieldParams )
        return -1;

    g_FieldMetadata =
            (*env)->GetFieldID( env, g_ClassRawMessage,
                                "strMetadata_", "Ljava/lang/String;");
    if( NULL == g_FieldMetadata )
        return -1;

    /*------------------------------------------------------------------------
     * Reflecting java.io.FileDescriptor
     * */
    g_ClassFileDescriptor =
            (*env)->FindClass(env, "java/io/FileDescriptor");
    if( NULL == g_ClassFileDescriptor )
        return -1;

    g_FDCTOR =
            (*env)->GetMethodID(env, g_ClassFileDescriptor, "<init>", "()V");
    if( NULL == g_FDCTOR )
        return -1;

    g_FieldRawFD =
            (*env)->GetFieldID(env, g_ClassFileDescriptor, "fd", "I");
    if( NULL == g_FieldRawFD )
        return -1;

    // Initialization succeeded. Flag up.
    g_JavaAccessorsInitialized = 1;

    return 0;
}


/*----------------------------------------------------------------------------
 *
 * */
JNIEXPORT void JNICALL
Java_org_openstack_storlet_sbus_SBusJNI_startLogger(    JNIEnv* env,
                                                        jobject obj,
                                                        jstring jLevel,
                                                        jstring jContId )
{
    const char* pLogLevel = (*env)->GetStringUTFChars( env, jLevel, NULL );
    if( NULL == pLogLevel )
        return;
    const char* pContId = (*env)->GetStringUTFChars( env, jContId, NULL );
        if( NULL == pContId )
                return;

    sbus_start_logger( pLogLevel, pContId);

    (*env)->ReleaseStringUTFChars( env, jLevel, pLogLevel );
}

/*----------------------------------------------------------------------------
 *
 * */
JNIEXPORT void JNICALL
Java_org_openstack_storlet_sbus_SBusJNI_stopLogger(     JNIEnv* env,
                                                        jobject obj )
{
    sbus_stop_logger();
}

/*----------------------------------------------------------------------------
 *
 * */
JNIEXPORT jint JNICALL
Java_org_openstack_storlet_sbus_SBusJNI_createSBus(     JNIEnv* env,
                                                        jobject obj,
                                                        jstring jstrPath )
{
    int nBus = -1;
    const char* pPath = (*env)->GetStringUTFChars( env, jstrPath, NULL );
    if( NULL == pPath )
        return -1;

    nBus = sbus_create( pPath);

    (*env)->ReleaseStringUTFChars( env, jstrPath, pPath );
    return nBus;
}

/*----------------------------------------------------------------------------
 *
 * */
JNIEXPORT jint JNICALL
Java_org_openstack_storlet_sbus_SBusJNI_listenSBus(     JNIEnv* env,
                                                        jobject obj,
                                                        jint    jnBus )
{
    return sbus_listen( jnBus );
}

/*----------------------------------------------------------------------------
 *
 * */
JNIEXPORT jint JNICALL
Java_org_openstack_storlet_sbus_SBusJNI_sendRawMessage(     JNIEnv* env,
                                                            jobject obj,
                                                            jstring jstrPath,
                                                            jobject jMsg )
{
    syslog( LOG_DEBUG, "Inside sendRawMessage" );
    if( init_java_accessors( env ) )
        return -1;

    int     i,j;
    int     nStatus             = 0;

    const char* strSBusPath     = 0;
    const char* strMetadata     = 0;
    int         nMetadataLen    = 0;
    const char* strParams       = 0;
    int         nParamsLen      = 0;
    int*        pFiles          = 0;
    int         nFiles          = 0;

    strSBusPath = (*env)->GetStringUTFChars( env, jstrPath, NULL );
    if( NULL == strSBusPath )
        return -1;

    jobjectArray jFileDscrArr =
            (jobjectArray)(*env)->GetObjectField(env, jMsg, g_FieldFDs );
    if( NULL != jFileDscrArr )
    {
        nFiles = (*env)->GetArrayLength(env, jFileDscrArr );
        pFiles = (int*) malloc( nFiles * sizeof(int) );
        for( i = 0; i < nFiles; ++i )
        {
            jobject jFileDscr =
                    (*env)->GetObjectArrayElement( env, jFileDscrArr, i );
            pFiles[i] = (*env)->GetIntField( env, jFileDscr, g_FieldRawFD );
        }
    }
    jstring jstrMetadata =
            (jstring)(*env)->GetObjectField(env, jMsg, g_FieldMetadata );
    if( NULL != jstrMetadata )
    {
        strMetadata = (*env)->GetStringUTFChars( env, jstrMetadata, NULL );
        nMetadataLen = strlen( strMetadata );
    }

    jstring jstrParams   =
            (jstring)(*env)->GetObjectField(env, jMsg, g_FieldParams );
    if( NULL != jstrParams )
    {
        strParams = (*env)->GetStringUTFChars( env, jstrParams, NULL );
        nParamsLen = strlen( strParams );
    }

    nStatus = sbus_send_msg(    strSBusPath,
                                pFiles, nFiles,
                                strMetadata, nMetadataLen,
                                strParams, nParamsLen );

    if( NULL != jstrMetadata )
        (*env)->ReleaseStringUTFChars( env, jstrMetadata,   strMetadata );
    if( NULL != jstrParams )
        (*env)->ReleaseStringUTFChars( env, jstrParams,     strParams );
    if( NULL != jFileDscrArr )
        free( pFiles );

    return nStatus;
}


/*----------------------------------------------------------------------------
 *
 * */
JNIEXPORT jobject JNICALL
Java_org_openstack_storlet_sbus_SBusJNI_receiveRawMessage(  JNIEnv* env,
                                                            jobject obj,
                                                            jint    jnBus )
{
    syslog( LOG_DEBUG, "JNI: Inside receiveRawMessage" );
    if( init_java_accessors( env ) )
        return NULL;

    int     i,j;
    int     nStatus         = 0;
    jobject RawMsgObj       = 0;

    char*   strMetadata     = 0;
    int     nMetadataLen    = 0;
    char*   strParams       = 0;
    int     nParamsLen      = 0;
    int*    pFiles          = 0;
    int     nFiles          = 0;


    nStatus = sbus_recv_msg(    jnBus,
                                &pFiles, &nFiles,
                                &strMetadata, &nMetadataLen,
                                &strParams, &nParamsLen );

    syslog( LOG_DEBUG, "JNI: sbus_recv_msg = %d, "
                       "nFiles = %d, "
                       "nMetadataLen = %d, "
                       "nParamsLen = %d",
                       nStatus, nFiles, nMetadataLen, nParamsLen );

    if( 0 <= nStatus )
    {
        strParams[nParamsLen] = '\0';
        // Create result object
        RawMsgObj = (*env)->NewObject( env,
                                       g_ClassRawMessage,
                                       g_RawMessageCTOR );

        // Params is never empty. We have 'command' at least.
        jstring jstrParams = (*env)->NewStringUTF( env, strParams );
        (*env)->SetObjectField( env, RawMsgObj, g_FieldParams, jstrParams );

        if( 0 < nFiles )
        {
            strMetadata[nMetadataLen] = '\0';
            // Instantiate FileDescriptor array
            jobjectArray jFileDscrArr =
                    (*env)->NewObjectArray( env, nFiles,
                                            g_ClassFileDescriptor,
                                            NULL );
            jobject jFileDscr;
            for( i = 0; i < nFiles; ++i )
            {
                jFileDscr = (*env)->NewObject( env,
                                               g_ClassFileDescriptor,
                                               g_FDCTOR );
                (*env)->SetIntField( env,
                                     jFileDscr,
                                     g_FieldRawFD,
                                     pFiles[i] );
                (*env)->SetObjectArrayElement( env,
                                               jFileDscrArr,
                                               i,
                                               jFileDscr );
            }
            // Assign obtained object
            (*env)->SetObjectField(env,RawMsgObj, g_FieldFDs, jFileDscrArr );

            jstring jstrMetadata = (*env)->NewStringUTF(env, strMetadata );
            (*env)->SetObjectField( env,
                                    RawMsgObj,
                                    g_FieldMetadata,
                                    jstrMetadata );
        }
        syslog(LOG_DEBUG, "receiveRawMessage: %d files", nFiles );

    }
    // Clean up
    free( pFiles );
    free( strMetadata );
    free( strParams );

    return RawMsgObj;
}

/*============================== END OF FILE ===============================*/

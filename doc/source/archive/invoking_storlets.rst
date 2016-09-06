===================
Storlets Invocation
===================

Once the storlet and its dependencies are deployed the storlet is ready for invocation.
Storlets can be invoked in 2 ways:

1. Invocation upon GET. In this case the user gets a transformation of the object residing in the store (as opposed to the actual object). Typical use case for GET is anonimization, where the user might not have access to a certain data unless it is being anonymized by some storlet.
2. Invocation upon PUT. In this case the data kept in the store is a transformation of the object uploaded by the user (as opposed to the actual uploaded data or metadata). A typical use case is metadata enrichment, where a Storlet extracts format specific metadata from the uploaded data and adds it as Swift metadata.

Invocation involves adding an extra header to the Swift original
PUT/GET requests. Following our Identity Storlet example given in <https://github.com/openstack/storlets/blob/master/doc/source/writing_and_deploying_storlets.rst>, here are invocation examples. This time the examples make use of the python swift client.

Invocation on GET
=================

The code below shows the invocation. Some notes:

#. There are invocations with and without a parameter controlling whether the
   get42 binary dependency is to be called. Note the difference in the response
   headers where one shows the execution result and the other does not.
#. Note the X-Run-Storlet header. being added to the call.
#. Note the X-Generate-Log storlet that causes a log file to be created.
   The execution results below show the log retrieval.

::

    from swiftclient import client as c
    
    def get_processed_object(url, token, storlet_name, container_name, object_name, invoke_get42 = False):
        headers = {'X-Run-Storlet': storlet_name,
                   'X-Storlet-Generate-Log' : 'True'}
        if (invoke_get42 == True):
            querystring = 'execute=true'
        else:
            querystring = None
    
        response_headers, object_content = c.get_object(url,
                                              token,
                                              container_name,
                                              object_name,
                                              query_string = querystring,
                                              response_dict=dict(),
                                              headers = headers)
        print response_headers
        print object_content
    
    AUTH_IP = '127.0.0.1'
    AUTH_PORT = '5000'
    ACCOUNT = 'service'
    USER_NAME = 'swift'
    PASSWORD = 'passw0rd'
    os_options = {'tenant_name': ACCOUNT}
    
    url, token = c.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT + "/v2.0", ACCOUNT +":"+USER_NAME, PASSWORD, os_options = os_options, auth_version="2.0")
    print 'Identity Storlet invocation without calling get42'
    get_processed_object(url, token, 'identitystorlet-1.0.jar', 'myobjects', 'source.txt')
    print 'Identity Storlet invocation instructing to call get42'
    get_processed_object(url, token, 'identitystorlet-1.0.jar', 'myobjects', 'source.txt', True)



Here is the result of the running the above python script:

::

    eranr@lnx-ccs8:/tmp$ python get_object_with_storlet.py
    Identity Storlet invocation without calling get42
    {
        'x-object-meta-x-object-meta-testkey': 'tester', 
        'transfer-encoding': 'chunked', 
        'accept-ranges': 'bytes', 
        'x-object-meta-testkey': 'tester', 
        'last-modified': 'Tue, 30 Sep 2014 22:07:42 GMT', 
        'etag': '8ca2a24dbd9779d462c66866c0fb90c3', 
        'x-timestamp': '1412114861.90504', 
        'x-trans-id': 'tx464a488a618e44b5b763d-00542baa25', 
        'date': 'Wed, 01 Oct 2014 07:15:50 GMT', 
        'x-object-meta-type': 'SBUS_FD_INPUT_OBJECT', 
        'content-type': 'application/octet-stream'
    }
    Some content to copy
    Identity Storlet invocation instructing to call get42
    {
        'x-object-meta-execution result': '42', 
        'x-object-meta-x-object-meta-testkey': 'tester', 
        'transfer-encoding': 'chunked', 
        'accept-ranges': 'bytes', 
        'x-object-meta-testkey': 'tester', 
        'last-modified': 'Tue, 30 Sep 2014 22:07:42 GMT', 
        'etag': '8ca2a24dbd9779d462c66866c0fb90c3', 
        'x-timestamp': '1412114861.90504', 
        'x-trans-id': 'tx12a4f2a168804dcabf8fc-00542baa26', 
        'date': 'Wed, 01 Oct 2014 07:15:50 GMT', 
        'x-object-meta-type': 'SBUS_FD_INPUT_OBJECT', 
        'content-type': 'application/octet-stream'
    }
    Some content to copy

We now show a download of the log file generated per the X-Storlet-Generate-Log header.
Again, we use the swift client assuming we have the appropriate environment variables in place.

Note that the log reflects the two invocations done above.

::

    eranr@lnx-ccs8:/tmp$ swift download storletlog identitystorlet.log
    identitystorlet.log [headers 0.243s, total 0.243s, 0.001 MB/s]
    eranr@lnx-ccs8:/tmp$ cat identitystorlet.log
    About to invoke storlet
    IdentityStorlet Invoked
    Storlet invocation done
    About to invoke storlet
    IdentityStorlet Invoked
    Exec = /home/swift/identitystorlet/get42
    Exit code = 42
    Storlet invocation done

Invocation on PUT
=================

the code below shows the invocation. Some notes:

#. As with the GET example there are invocations with and without a parameter controlling whether the get42 binary dependency is to be called. After each put we do a GET and print the response headers to show the difference between the invocations. See below.
#. As with the GET example we add the X-Run-Storlet header.
#. This time we do not add the X-Generate-Log header, which is the recommended way, as it saves a creation of an object.

::

    import random
    import string
    from swiftclient import client as c
    
    def put_processed_object(url, token, storlet_name, container_name, object_name, file_name_to_upload, invoke_get42 = False):
        headers = {'X-Run-Storlet': storlet_name,
                   'X-Storlet-Generate-Log' : 'True'}
        if (invoke_get42 == True):
            querystring = 'execute=true'
        else:
            querystring = None
    
        fileobj = open(file_name_to_upload,'r')
        random_md = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        headers = {'X-Run-Storlet': 'identitystorlet-1.0.jar', 'X-Object-Meta-Testkey' : random_md}
        c.put_object(url,
                     token,
                     container_name,
                     object_name,
                     fileobj,
                     headers = headers,
                     query_string = querystring,
                     response_dict=dict())
    
        resp_headers, saved_content = c.get_object(
                    url,
                    token,
                    container_name,
                    object_name,
                    response_dict=dict())
        print resp_headers
    
    AUTH_IP = '127.0.0.1'
    AUTH_PORT = '5000'
    ACCOUNT = 'service'
    USER_NAME = 'swift'
    PASSWORD = 'passw0rd'
    os_options = {'tenant_name': ACCOUNT}
    
    url, token = c.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT + "/v2.0", ACCOUNT +":"+USER_NAME, PASSWORD, os_options = os_options, auth_version="2.0")
    print 'Identity Storlet invocation without calling get42'
    put_processed_object(url, token, 'identitystorlet-1.0.jar', 'myobjects', 'source.txt', '/tmp/source.txt')
    print 'Identity Storlet invocation instructing to call get42'
    put_processed_object(url, token, 'identitystorlet-1.0.jar', 'myobjects', 'source.txt', '/tmp/source.txt' , True)



Here is the result of the running the above python script:

::

    eranr@lnx-ccs8:/tmp$ python put_object_with_storlet.py
    Identity Storlet invocation without calling get42
    {
        'content-length': '1024', 
        'x-object-meta-x-object-meta-testkey': '1185FZ5FPQ1WXS9IDT4TZZB6GYAQQ0WL', 
        'accept-ranges': 'bytes', 
        'x-object-meta-testkey': '1185FZ5FPQ1WXS9IDT4TZZB6GYAQQ0WL', 
        'last-modified': 'Wed, 01 Oct 2014 07:48:56 GMT', 
        'etag': '7575c5b098f45ccabce1c3f7fc906eb9', 
        'x-timestamp': '1412149735.87168', 
        'x-trans-id': 'tx9a27ba91bee34a8ca9f0c-00542bb1e7', 
        'date': 'Wed, 01 Oct 2014 07:48:55 GMT', 
        'x-object-meta-type': 'SBUS_FD_INPUT_OBJECT', 
        'content-type': 'text/plain'
    }
    Identity Storlet invocation instructing to call get42
    {
        'x-object-meta-execution result': '42', 
        'content-length': '1024', 
        'x-object-meta-x-object-meta-testkey': '54YA1EDTTODMBUJOYCHEGSOQQPV0180L', // This looks like a bug
        'accept-ranges': 'bytes', 
        'x-object-meta-testkey': '54YA1EDTTODMBUJOYCHEGSOQQPV0180L', 
        'last-modified': 'Wed, 01 Oct 2014 07:48:56 GMT', 
        'etag': '7575c5b098f45ccabce1c3f7fc906eb9', 
        'x-timestamp': '1412149735.97100', 
        'x-trans-id': 'txde8619a966c14b0c99d97-00542bb1e8', 
        'date': 'Wed, 01 Oct 2014 07:48:56 GMT', 
        'x-object-meta-type': 'SBUS_FD_INPUT_OBJECT', 
        'content-type': 'text/plain'
    }

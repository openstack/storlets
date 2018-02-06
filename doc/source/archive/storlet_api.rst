===============
Storlets API v1
===============


Swift Storlets extend Swift with the capability to run computation near the data
in a secure and isolated manner.
With Swift Storlets a user can write code, package and deploy it as a Swift object,
and then explicitly invoke it on data objects as if the code was part of the Swift pipeline.
We use the term Storlet to refer to the binary code deployed as a Swift object.
Invoking a Storlet on a data object is done in an isolated manner so that the data
accessible by the computation is only the object's data and its user metadata.
Moreover, the computation has no access to disks, network or to the Swift request environment.

Operations on Storlets
======================

Storlets are uploaded to a special container called 'storlet'.
Therefore, '/storlet' shows up in the url of various operations,
such as to upload a storlet or to list all of the available storlets.

List All Storlets
-----------------

::

 [GET] /v1/{account}/storlet

The body of the response contains a list of the names of the uploaded storlets.
The Content-type of the response is (text/plain).

::

            storlet1.jar
            storlet2.jar
            storlet3.jar


Upload a New Storlet
--------------------

You may write a storlet in Java according to the instructions in the Developer's manual and upload it to the Object Store.
The storlet is uploaded to the container named 'storlet', so '/storlet' appears in the url.
The storlet may depend on other existing libraries, which must be uploaded to the dependency container.
When uploading a storlet,
the X-Object-Meta-Storlet-Dependency header requires a value that is a comma separated list of dependencies.
The main_class_name parameter for the X-Object-Meta-Storlet-Main header specifies the class in which the invoke
method of the storlet is defined.
The X-Object-Meta-Storlet-Language header specified the language in which the storlet is run.
At present, only 'Java' is supported.
The X-Object-Meta-Storlet-Interface-Version header should be provided and set to the value '1.0'.
Although not currently used, the X-Object-Meta-Storlet-Object-Metadata header must be provided and set to 'no'.
See the Storlets Developer's manual for details of the signature of the invoke method.
The content-type of the request should be set to 'application/octet-stream'.
Additional details and examples can be found at <https://github.com/openstack/storlets/blob/master/doc/source/writing_and_deploying_storlets.rst>.

::

 [PUT] /v1/{account}/storlet/{storlet_object_name}

::

    'X-Object-Meta-Storlet-Language' :   'Java'
    'X-Object-Meta-Storlet-Interface-Version' :   '1.0'
    'X-Object-Meta-Storlet-Dependency': dependencies
    'X-Object-Meta-Storlet-Object-Metadata' : 'no'
    'X-Object-Meta-Storlet-Main': {main_class_name}
    'X-Auth-Token': {authorization_token}




Operations on dependencies
==========================

Upload a New Dependency
-----------------------

You may create and upload your own libraries to assist in running a storlet.
These dependencies are uploaded to a special container named 'dependency'.
For an executable dependency (such as a compiled c program),
you must specify the X-Object-Meta-Storlet-Dependency-Permissions header.
Otherwise, that header may be omitted.
The name of the library containing the dependency (i.e. dependency_name) goes into the URI.
The content-type of the request should be set to 'application/octet-stream'.

::

 [PUT] /v1/{account}/dependency/{dependency_object_name}

::

    'X-Object-Meta-Storlet-Dependency-Version': '1'
    'X-Object-Meta-Storlet-Dependency-Permissions' : '0755'
    'X-Auth-Token': {authorization_token}



Storlets Invocation
===================

Once the storlet and its dependencies are deployed the storlet is ready for invocation.
Storlets can be invoked in 3 ways:

#. Invocation upon GET.
    In this case the user gets a transformation of the object residing in the store (as opposed to the actual object).
    One use case for GET is anonymization, where the user might not have access to certain data unless it is
    being anonymized by some storlet.

#. Invocation upon PUT.
    In this case the data kept in the object store is a transformation of the object uploaded by the user
    (as opposed to the original data or metadata).
    A typical use case is metadata enrichment, where a Storlet extracts format specific metadata from the uploaded data
    and adds it as Swift metadata.

#. Invocation upon COPY.
    In this case the storlet acts on data that is in the object store, generating a new object. A typical use case is
    thumbnail extraction from an existing jpg.

Invocation involves adding an extra header ('X-Run-Storlet') to the Swift original PUT/GET/COPY requests.
Additional details and examples can be found in <https://github.com/openstack/storlets/blob/master/doc/source/archive/invoking_storlets.rst>.

Invoke a storlet upon object download
-------------------------------------

::

 [GET] /v1/{account}/{container}/{object}

An additional header ('X-Run-Storlet') must be provided to inform the system to run a storlet.

::

    'X-Run-Storlet': {storlet_name}
    'X-Auth-Token': {authorization_token}

One may also provide parameters to the storlet. There are two ways to send parameters:

#. Through the URL query string. For instance: /v1/{account}/{container}/{object}?param1=val1&param2=val2

#. Through the request headers. For instance:

    ::

        'X-Storlet-Parameter-1': 'param1:val1'
        'X-Storlet-Parameter-2': 'param2:val2'

Parameters that start with 'storlet\_' are not allowed. The 'storlet\_' prefix is reserved for internal system use.

To invoke a storlet on a range of an object use the 'X-Storlet-Range' header. For instance:

    ::

        'X-Storlet-Range': 'bytes=1-6'

'X-Storlet-Range' can take any value that Swift can take for the HTTP 'Range' header as described in <https://developer.openstack.org/api-ref/object-store/index.html>.
Specifying HTTP 'Range' header together with 'X-Run-Storlet' is not allowed, and results in '400 Bad Request'

Invoke a storlet upon object upload
-----------------------------------

::

 [PUT] /v1/{account}/{container}/{object}

An additional header ('X-Run-Storlet') must be provided to inform the system to run a storlet.

::

    'X-Run-Storlet': {storlet_name}
    'X-Auth-Token': {authorization_token}

As with the invocation upon download, one may provide parameters to the storlet either through the URL query string or through
the request headers.

Invoke a storlet upon object copy
---------------------------------

Object copy in Swift can be done using both the PUT and the COPY verbs as shown below

::

 [PUT] /v1/{account}/{container}/{object}
   'X-Copy-From': {source container}/{source object}

 [COPY] /v1/{account}/{container}/{object}
   'Destination': {dest container}/{dest object}

An additional header ('X-Run-Storlet') must be provided to inform the system to run a storlet.

::

    'X-Run-Storlet': {storlet_name}
    'X-Auth-Token': {authorization_token}

In the PUT case the storlet acts upon the object appearing in the 'X-Copy-From' header, creating the object appearing in the request path.
In the COPY case the storlet acts upon the object appeairng in the requets path, crating the object appearing in the 'Destination' header.

Specifying any of the headers below while invoking a storlet upon copy will result in '400 Bad Request'
 - 'X-Copy-From-Account'
 - 'Destination-Account'
 - 'X-Fresh-Metadata'

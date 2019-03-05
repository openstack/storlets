Storlets API v1
===============
The storlets API is an extension of the Swift API. In some cases we use
the Swift API as is. For example, uploading a storlet is done using Swift upload
to a designated container. In other cases we add storlets specific headers
to existing Swift operations. For example invoking a storlet on download is done
by adding the 'X-Run-Storlet' header to the Swift download operation.

Operations on Storlets
======================

Storlets are stored to a special container called 'storlet'.

.. note::

    The name of the container where storlets are uploaded to is configurable. The name 'storlet' is the default.

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

You may write a storlet in Java or Python according to the instructions in the storlet developer guide and upload it to the Object Store.
The storlet is uploaded to the container named 'storlet', so '/storlet' appears in the url.
The storlet may depend on other existing libraries, which must be uploaded to the 'dependency' container.

.. note::

    Once again, the name 'dependency' is a default, and can be configured differently.

When uploading a storlet,
the X-Object-Meta-Storlet-Dependency header requires a value that is a comma separated list of dependencies.
The main_class_name parameter for the X-Object-Meta-Storlet-Main header specifies the class in which the invoke
method of the storlet is defined. For python written storlets, this parameter should be prefixed with the python
module name. For example, if the storlet file is named 'mystorlet.py', then the class name must be
'mystorlet.<class name>'.
The X-Object-Meta-Storlet-Language header specified the language in which the storlet is run.
Either "Python" or "Java" is available for the value.
The X-Object-Meta-Storlet-Interface-Version header should be provided and set to the value '1.0'.
Although not currently used, the X-Object-Meta-Storlet-Object-Metadata header must be provided and set to 'no'.
See the Storlets Developer's manual for details of the signature of the invoke method.
The content-type of the request should be set to 'application/octet-stream'. Only in Python, you may
set 'X-Object-Meta-Storlet-Language-Version' to choose your python interpreter version.

::

 [PUT] /v1/{account}/storlet/{storlet_object_name}

For Java written storlets

::

    'X-Object-Meta-Storlet-Language': 'Java'
    'X-Object-Meta-Storlet-Interface-Version': '1.0'
    'X-Object-Meta-Storlet-Dependency': dependencies
    'X-Object-Meta-Storlet-Object-Metadata': 'no'
    'X-Object-Meta-Storlet-Main': {main_class_name}
    'X-Auth-Token': {authorization_token}

For Python written storlets

::

    'X-Object-Meta-Storlet-Language': 'Python'
    'X-Object-Meta-Storlet-Language-Version': '2.7'
    'X-Object-Meta-Storlet-Interface-Version': '1.0'
    'X-Object-Meta-Storlet-Dependency': dependencies
    'X-Object-Meta-Storlet-Object-Metadata': 'no'
    'X-Object-Meta-Storlet-Main': {module_name.class_name}
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

#. Invocation upon object download.
    In this case the user gets a transformation of the object residing in the store (as opposed to the actual object).
    One use case for GET is anonymization, where the user might not have access to certain data unless it is
    being anonymized by some storlet. Typically, when invoking a storlet upon object download, the storlet will
    be invoked on a storage node that holds a copy of the object. Exceptions to this rule are detailed below.

#. Invocation upon object upload.
    In this case the data kept in the object store is a transformation of the object uploaded by the user
    (as opposed to the original data or metadata).
    A typical use case is metadata enrichment, where a Storlet extracts format specific metadata from the uploaded data
    and adds it as Swift metadata. When invoking a storlet upon object upload, the storlet will be invoked on a proxy node,
    prior to replication. Thus, the computation happens only once, and not once per replica.

#. Invocation upon object copy.
    In this case the storlet acts on data that is in the object store, generating a new object. A typical use case is
    thumbnail extraction from an existing jpg. The location where the storlet is invoked on copy (object node or proxy node)
    is the same as for the download case.

Below is the API reference of the abovementioned invocations.

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

'X-Storlet-Range' can take any value that Swift can take for the HTTP 'Range' header as described in <http://developer.openstack.org/api-ref-objectstorage-v1.html>.
Specifying HTTP 'Range' header together with 'X-Run-Storlet' is not allowed, and results in '400 Bad Request'

.. note::

   In case the object happens to be an SLO the storlet is invoked over the entire object data. Thus, the storlet is invoked on a proxy node.

It is possible to invoke a storlet on GET over more then one object. This is done using the 'X-Storlet-Extra-Resources' header, that can be used
to specify a comma separated list of object paths of the form <container>/<object>. Currently, cross account extra resources are not supported.
In the below GET example the multi input storlet will get 3 object input streams.

::

  [GET] /v1/AUTH_1234/my_container/myobject_1

  'X-Run-Storlet': 'multiinputstorlet-1.0.jar'
  'X-Storlet-Extra-Resources': 'my_other_container/my_other_object', 'my_other_other_container/my_other_other_object'
  'X-Auth-Token': {authorization_token}

When using 'X-Storlet-Extra-Resources' the storlet is invoked on a proxy node.

.. note::

  Refer to the multi-input-storlet source for writing a storlet that processes multiple inputs.

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

Independently of the verb used to invoke a copy, one can add the 'X-Storlet-Extra-Resources' header. Thus, one can e.g. create an
object which is a concatenation of the copy source and the extra resources. As with the invocation upon downlod, when using extra
resources, the storlet is invoked on a proxy node.

Currently, specifying any of the headers below while invoking a storlet upon copy will result in '400 Bad Request'
 - 'X-Copy-From-Account'
 - 'Destination-Account'
 - 'X-Fresh-Metadata'

Executing a storlet on proxy servers only
-----------------------------------------
Use the 'X-Storlet-Run-On-Proxy' header to enforce the engine to invoke the storlet on the proxy, e.g.:

::

    'X-Storlet-Run-On-Proxy': ''

Storlets ACLs
=============

Storlets ACLs are an extension to Swift's container read acl that allow to give users access to data through a storlet.
In other words, a certain user may not have access to read objects from a container unless the access is done through
a specific storlet. Setting storlets ACLs is done using the POST verb on a container as follows:

::

  [POST] /v1/{account}/{container}

::

  X-Storlet-Container-Read: {user_name}
  X-Storlet-Name: {storlet_name}
  X-Auth-Token: {authorization_token}

#. The user_name must be a user defined in Keystone, that can retrieve a valid token.

#. The storlet_name is the name of the storlet through which access is permitted. This name
    should match the name specified when running a storlet (see storlet invocation above)

#. The authorization_token is a token of the POST request initiator, which must have
    privilege to set the container ACL

Currently, a storlet ACL can be set only for a single user. Storlets ACLs can be viewed
as any other container read ACL by performing HEAD request on the container. The ACL
will be shown as .r:storlets.<user_name>_<storlet_name> as part of the Container-Read-ACL.

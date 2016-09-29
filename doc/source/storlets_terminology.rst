Storlets Terminology
====================
The overall storlets mechanism involves a lot of moving parts as well as
poeple or roles involved throughout the usage of the system. We give below
a definition of the various terms used throughout the documentation.

Storlet
-------
A storlet is the binary code deployed as a Swift object. Invoking a storlet
on a data object is done in an isolated manner so that the data accessible
by the computation is only the object's data and its associated metadata.
Moreover, the computation has no access to disks, network or to the Swift
request environment.

While storlets give way to perform computation over data in the object store,
they are not meant for general purpose processing.
Specifically, they are not meant for processing that requires a large
temporary state. Being executed inside a well controlled run time environment
(e.g. a Docker container) they cannot use too much memory and it is not advisable
for storlets to create temporary files.

Writing a storlet involves implementing a well defined interface called invoke.
In a nutshell this interface consists of an input stream, an output stream and a logger.
The storlet is assumed to read from the input stream, do its thing, and write the result
to the output stream.

Storlet Invocation
------------------
A storlet invocation is a user request wishing to perform a storlet computation
over a specific data object in Swift. A storlet can be invoked over data in 3
different ways:

#. Invoke a storlet on object download. When invoking a storlet this way, the user
   gets the storlet transformation over the object's data (and metadata), rather then
   the data and metadata as stored in Swift.
#. Invoke a storlet on object upload. When invoking a storlet this way, the data
   stored in Swift is the storlet transformation over the uploaded data (and metadata)
   rather then the uploaded data and metadata.
#. Invoke a storlet on object copy. This is a way to invoke a storlet over an existing
   data object, where the storlet's output is kept in a newly crerated object. In a regular
   Swift copy the newly created object is a identical to the source object.

The Storlet Engine
------------------
The storlet engine is the underlying mechanism that can take a storlet as a Swift object
and invoke it over Swift data objects in an isolated manner (inside a Docker container).
In a nutshell the engine intercepts invocation requests, route the input data stream into
the storlet and receives back the storlet output stream. The engine is implemented as a Swift
middleware.

Roles
=====

Storlet Developer
-----------------
The storlet developer develops, packages and deploys storlets to Swift.
Deploying a storlet is essentially uploading it (and its potential
dependencies) to designated containers in Swift. Thus, the storlet
developer is assumed to have access those containers.

Storlet User
------------
A Swift user that wishes to invoke a storlet on a data object
in Swift. The invoking user must have access to that data as well
as read access to the storlet object.

Storlets Account Manager
------------------------
Account manager in short. The account manager is an admin user on
the customer side who is typically the one responsible for paying the bill
(and perhaps setting ACLs). From storlets perspective the account manager
is responsible for managing the Docker image as well as the storlets that
can be executed on data in the account. Note that all storlets executions
being done on data in a certain account are within the same Docker container.

Swift Storlet Manager
---------------------
Typically, this is the Swift admin on the provider side that deals with rings
and broken disks. From the storlets perspective (s)he is the one responsible
for deploying the account manager Docker image across the cluster (needless
to say that here is a default image).
This allows the account admin to upload a self tailored Docker image that the
Swift admin can then deploy across the cluster.

Storlet Engine Developer
------------------------
Someone wishing to take part and contribute to the Openstack Storlets project.

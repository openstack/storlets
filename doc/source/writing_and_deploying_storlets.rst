Storlet writing and deploying guide
===================================

Storlets can be written either in Java or in Python. This guide
is a language independent starting point for writing
and deploying storlets. The Java_ and Python_ specific guides
complement this guide and should be read next after this one.

.. _Java: writing_and_deploying_java_storlets.html
.. _Python: writing_and_deploying_python_storlets.html


Writing a storlet involves implementing a single function referred to
as invoke (the exact name varies between languages).

Typically, the invoke operation gets an input stream and an
output stream. The input stream will contain the data either being uploaded
(in case the storlet is invoked during upload) or being downloaded (when
the invocation is done during download). The input stream is accompanied with
metadata that reflects the Swift user defined metadata. The output stream
exposes a way to write back not only the storlet output data, but also the
metadata. The input and output streams are exposed to the storlet code
in a way that is native to the language being used.

Once the storlet is written and tested it can be uploaded as an object to a
designated container (called 'storlet' by default). Storlet code external
dependencies such as Java libraries or Python modules can be uploaded as well.
It is assumed, however, that storlet dependencies are relatively small
(on the order of few MBs). Heavier dependencies should be part of the Docker
image. Deploying storlets and dependencies are covered below.

There are various implementations of storlets in the StorletSamples/java
and StorletSamples/python directories. These storlets are used by the engine's
functional tests.

The next two sections describe storlet writing and deploying guidelines that are
independent of the language used.

Storlet Writing Guidelines
==========================
Independent of the language used for writing a storlet, there are several guidelines
to follow. Some of them are musts and some are recommendations.

Recommendations
---------------

#. Storlets are tailored for stream processing, that is, they process the input as it
   is read and produce output while still reading. In other words a 'merge sort'
   of the content of an object is not a good example for a storlet as it requires
   to read all the content into memory (random reads are not an option as the
   input is provided as a stream). While we currently do not employ any restrictions
   on the CPU usage or memory consumption of the storlet, reading large object
   into memory or doing very intensive computations would have impact on the overall
   system performance.

#. While this might be obvious make sure to unit test your storlet prior to deploying it.

Musts
-----

#. The storlet code must be thread safe and re-enterant. The invoke method will
   be called many times and potentially in parallel.

#. Once the storlet has finished writing the response, it is important to close
   the output stream. Failing to do so will result in a timeout.

#. A storlet must start to respond within 40 seconds of invocation. Otherwise,
   Swift would timeout. Moreover, the storlet must output something every 40 seconds
   so as not to timeout. This is a mechanism to ensure that the storlet code does not
   get stuck. Note that outputting an empty string does not do the job in terms of
   resetting the 40 seconds timeout.

#. The storlet must write metadata to the output stream, and must do so before it
   starts streaming out the data. A typical implementation would read the
   input metadata and use it as a basis for the metadata being written.
   Note the applicability of the 40 seconds timeout here as well.

#. The total size of metadata that can be set (when serialized as a string)
   must not exceed 4096 Bytes

#. While Swift uses the prefix X-Object-Meta to specify that a certain header
   reflects a metadata key, the key itself should not begin with that prefix.
   More specifically, metadata keys being set by the storlet should not have that
   prefix (unless this is really part of the key)

Storlet Deployment Guidelines
=============================

Storlet deployment is essentially uploading the storlet and its dependencies to
designated containers in the account you are working with. While a storlet and a
dependency are regular Swift objects, they must carry some metadata used by the
storlet engine. When a storlet is first executed, the engine fetches the necessary
objects from Swift and puts them in a directory accessible to the Docker container.
Note that the dependencies are meant to be small. Having a large list of dependencies
or a very large dependency may result in a timeout on the first attempt to execute a
storlet. If this happens, just re-send the request again.

We support two types of dependencies:

#. External libraries or modules that
   are native to the storlet language

#. Executables dependency that the storlet code
   can execute.

Storlet Object Metadata
-----------------------
Uploading a storlet must be done to a designated container, called by default "storlet". The uploaded object
must carry the following metadata. See the specific langauge guides for more information.

   ::

        X-Object-Meta-Storlet-Language - must be 'python' or 'java'
        X-Object-Meta-Storlet-Interface-Version - currenltly we have a single version '1.0'
        X-Object-Meta-Storlet-Object-Metadata - Currently, not in use, but must appear. Use the value 'no'
        X-Object-Meta-Storlet-Main - The name of the class that implements the invoke operation

Optional metadata item is:

  ::

        X-Object-Meta-Storlet-Dependency - A comma separated list of dependencies.

If one wishes to update the storlet just upload again, the engine would recognize
the update and bring the updated code.

Dependency Object Metadata
--------------------------
Uploading a dependency must be done to a designated container, called by default "dependency". The uploaded object
must carry the following metadata.

   ::

        X-Object-Meta-Storlet-Dependency-Version - While the engine currently does not parse this header, it must appear.

Optional metadata item is:

   ::

        X-Object-Meta-Storlet-Dependency-Permissions - The permissions given to the dependency when it is copied to the
        Docker container. This is helpful for binary dependencies invoked by the storlet.
        For a binary dependency once can specify: '0755'


.. note:: Currently, dependency updates are not recognized.


Deploying a Storlet using Swift Client cli
------------------------------------------
We show below how to deploy a storlet using the Swift client cli.
The example uses a Java storlet. The differences from deploying a
Python storlet are minor and we highlight them where required.

When using the Swift client one needs to provide the credentials, as well as the
authentication URI. The credentials can be supplied either via environment
variables or via command line parameters. To make the commands more readable we
use environment variables as shown below. The actual values are aligned with the
development environment installation instructions_

.. _instructions: engine_dev_installation.html

::

  export OS_USERNAME=tester
  export OS_PASSWORD=testing
  export OS_TENANT_NAME=test
  export OS_AUTH_URL=http://127.0.0.1:5000/v2.0

Here is the Swift client command for uploading the storlet. some notes:

#. We use the upload option of the swift cli.
#. The container name is the first parameter for the upload command and is
   'storlet'
#. The name of the object and the local file to upload is 'identitystorelt-1.0-jar'
   IMPORTANT: when uploading the file from another directory, that parameter would
   be something of the form 'bin/identitystorelt-1.0-jar' in this case the name
   of the object appearing in the storlet container would be 'bin/identitystorelt-1.0-jar'
   which will not work for the engine.
#. The metadata that needs to accompany the storlet object is provided as headers.

::

  eranr@lnx-ccs8:~/workspace/Storlets/StorletSamples/IdentityStorlet/bin$ swift upload storlet identitystorlet-1.0.jar \
  -H "X-Object-Meta-Storlet-Language:Java" \
  -H "X-Object-Meta-Storlet-Interface-Version:1.0" \
  -H "X-Object-Meta-Storlet-Object-Metadata:no" \
  -H "X-Object-Meta-Storlet-Main:org.openstack.storlet.identity.IdentityStorlet" \
  -H "X-Object-Meta-Storlet-Dependency:get42"

.. note:: When deploying a Python storlet the name of the object (identitystorlet-1.0.jar in the above) has a different format
          Otherwise, "X-Object-Meta-Storlet-Language" is "Python", and "X-Object-Meta-Storlet-Main" has a different format.
          Please refer to Python_ for the exact details.

Here is the Swift client command for uploading the get42 dependency. Again,
some notes:

#. The container name used here is the first parameter for the upload command and is 'dependency'.

#. We use the optional permissions header as this is a binary .

::

  eranr@lnx-ccs8:~/workspace/Storlets/StorletSamples/IdentityStorlet/bin$ swift upload dependency get42 \
  -H "X-Object-Meta-Storlet-Dependency-Version:1.0" \
  -H "X-Object-Meta-Storlet-Dependency-Permissions:0755"

Deploying a Storlet using the Python Swift Client
-------------------------------------------------

Here is a code snippet that uploads both the storlet as well as the dependencies.
The code assumes v2 authentication, and was tested against a Swift cluster with:

#. Keystone configured with a 'test' account, having a user 'tester' whose
   password is 'testing'
#. Under the service account there are already 'storlet' and 'dependency'
   containers.

The example uses a Java storlet. The differences from deploying a
Python storlet are minor and are the same as the differences highlighted
in the deployment using Swift client section above.

::

  from swiftclient import client

  def put_storlet_object(url, token, storlet_name, local_path_to_storlet, main_class_name, dependencies):
      # Delete previous storlet
      resp = dict()

      metadata = {'X-Object-Meta-Storlet-Language':'Java',
                  'X-Object-Meta-Storlet-Interface-Version':'1.0',
                  'X-Object-Meta-Storlet-Dependency': dependencies,
                  'X-Object-Meta-Storlet-Object-Metadata':'no',
                  'X-Object-Meta-Storlet-Main': main_class_name}
      f = open('%s/%s' % (local_path_to_storlet, storlet_name), 'r')
      content_length = None
      response = dict()
      client.put_object(url, token, 'storlet', storlet_name, f,
                        content_length, None, None,
                        "application/octet-stream",
                        metadata,
                        None, None, None,
                        response)
      print response
      f.close()

  def put_storlet_dependency(url, token, dependency_name, local_path_to_dependency):
      metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1'}
      # for an executable dependency
      # metadata['X-Object-Meta-Storlet-Dependency-Permissions'] = '0755'
      f = open('%s/%s'% (local_path_to_dependency, dependency_name), 'r')
      content_length = None
      response = dict()
      client.put_object(url, token, 'dependency', dependency_name, f,
                        content_length, None, None,
                        "application/octet-stream",
                        metadata,
                        None, None, None,
                        response)
      print response
      f.close()
      status = response.get('status')
      assert (status == 200 or status == 201)

  AUTH_IP = '127.0.0.1'
  AUTH_PORT = '5000'
  ACCOUNT = 'test'
  USER_NAME = 'tester'
  PASSWORD = 'testing'
  os_options = {'tenant_name': ACCOUNT}

  url, token = client.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT + "/v2.0", ACCOUNT +":"+USER_NAME,
                               PASSWORD,
                               os_options = os_options,
                               auth_version="2.0")
  put_storlet_object(url, token,'identitystorlet-1.0.jar','/tmp',
                     'org.openstack.storlet.identity.IdentityStorlet',
                     'get42')
  put_storlet_dependency(url, token,'get42','/tmp')


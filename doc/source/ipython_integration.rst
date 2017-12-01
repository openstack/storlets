IPython Notebook Integration
============================

IPython/Jupyter provides a browser based interactive shell that supports data visualization. The storlets integration with IPython allows an easy deployment and invocation of storlets via an IPython notebook. In the below sections we describe how to setup IPython notebook to work with storlets, how to deploy a python storlet and how to invoke a storlet.

Set up IPython to work with storlets
------------------------------------
Setting up an IPython notebook to work with storlets involves:

#. Providing the authentication information of a storlet enabled Swift account.
    This is done by setting environment variables similar to those used by swift
    client. The exact variables that need to be set are dependent on the auth middleware
    used and the auth protocol version. For more details please refer to:
   `python-swiftclient docs
   <https://docs.openstack.org/python-swiftclient/latest/cli/index.html#authentication>`_.

#. Load the storlets IPython extension.

The below shows environment variables definitions that comply with the
default storlets development environment installation (`s2aio <http://storlets.readthedocs.io/en/latest/s2aio.html>`__).

  ::

    import os
    os.environ['OS_AUTH_VERSION'] = '3'
    os.environ['OS_AUTH_URL'] = 'http://127.0.0.1/v3'
    os.environ['OS_USERNAME'] = 'tester'
    os.environ['OS_PASSWORD'] = 'testing'
    os.environ['OS_USER_DOMAIN_NAME'] = 'default'
    os.environ['OS_PROJECT_DOMAIN_NAME'] = 'default'
    os.environ['OS_PROJECT_NAME'] = 'test'

To load the storlets IPython extension simply enter and execute the below:

::

  %load_ext storlets.tools.extensions.ipython

Deploy a Python storlet
-----------------------
General background on storlets deployment is found `here <http://storlets.readthedocs.io/en/latest/writing_and_deploying_storlets.html#storlet-deployment-guidelines>`__.

In a new notebook cell, enter the '%%storletapp' directive
followed by the storlet name. Followng that type the storlet code.
Below is an example of a simple 'identitiy' storlet.
Executing the cell will deploy the storlet into Swift.

::

  %%storletapp test.TestStorlet

  class TestStorlet(object):
      def __init__(self, logger):
          self.logger = logger

      def __call__(self, in_files, out_files, params):
          """
          The function called for storlet invocation
          :param in_files: a list of StorletInputFile
          :param out_files: a list of StorletOutputFile
          :param params: a dict of request parameters
          """
          self.logger.debug('Returning metadata')
          metadata = in_files[0].get_metadata()
          for key in params.keys():
            metadata[key] = params[key]
          out_files[0].set_metadata(metadata)

          self.logger.debug('Start to return object data')
          content = ''
          while True:
              buf = in_files[0].read(16)
              if not buf:
                  break
              content += buf
          self.logger.debug('Received %d bytes' % len(content))
          self.logger.debug('Writing back %d bytes' % len(content))
          out_files[0].write(content)
          self.logger.debug('Complete')
          in_files[0].close()
          out_files[0].close()

.. note:: To run the storlet on an actual data set, one can enter the following at
  the top of the cell

::

  %%storletapp test.TestStorlet --with-invoke --input path:/<container>/<object> --print-result

N.B. Useful commands such as 'dry-run'  is under development. And more
details for options are in the next section.

Invoke a storlet
----------------
General information on storlet invocation can be found `here <http://storlets.readthedocs.io/en/latest/api/overview_api.html#storlets-invocation>`__.

Here is how an invocation works:

#. Define an optional dictionay variable params that would hold the invocation parameters:

    ::

        myparams = {'color' : 'red'}

#. To invoke test.TestStorlet on a get just type the following:

    ::

    %get --storlet test.py --input path:/<container>/<object>  -i myparams -o myresult

The invocation will execute test.py over the specified swift object with parameters read from myparams.
The result is placed in myresults.
The '-i' argument is optional, however, if specified the supplied value must be a name of a defined dictionary variable.
myresults is an instance of storlets.tools.extensions.ipython.Response. This class has the following members:

#. status - An integer holding the Http response status

#. headers - A dictionary holding the storlet invocation response headers

#. iter_content - An iterator over the response body

#. content - The content of the response body


#. To invoke test.TestStorlet on a put just type the following:

    ::

    %put --storlet test.py --input <full path to local file> --output path:/<container>/<object>  -i myparams -o myresult

The invocation will execute test.py over the uploaded file specified with the --input option which must be a full local path.
test.py is invoked with parameters read from myparams.
The result is placed in myresults.
The '-i' argument is optional, however, if specified the supplied value must be a name of a defined variable.
myresults is a dictionary with the following keys:

#. status - An integer holding the Http response status

#. headers - A dictionary holding the storlet invocation response headers

#. To invoke test.TestStorlet on a copy just type the following:

    ::

    %copy --storlet test.py --input path:/<container>/<object> --output path:/<container>/<object>  -i myparams -o myresult

The invocation will execute test.py over the input object specified with the --input option.
The execution result will be saved in the output object specified with the --output option.
test.py is invoked with parameters read from myparams.
The result is placed in myresults.
The '-i' argument is optional, however, if specified the supplied value must be a name of a defined variable.
myresults is a dictionary with the following keys:

#. status - An integer holding the Http response status

#. headers - A dictionary holding the storlet invocation response headers


Extension docs
^^^^^^^^^^^^^^

.. automodule:: storlets.tools.extensions.ipython
    :members:
    :show-inheritance:

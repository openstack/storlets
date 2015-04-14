==============
Swift Storlets
==============

Introduction
============
Swift Storlets extend Swift with the capability to run computation near the data in a secure and isolated manner. With Swift Storlets a user can write code,
package and deploy it as a Swift object, and then explicitly invoke it on data objects as if the code was part of the Swift pipeline.
We use the term Storlet to refer to the binary code deployed as a Swift object.
Invoking a Storlet on a data object is done in an isolated manner so that the data accessible by the computation is only the object's data and its user metadata.
Moreover, the computation has no access to disks, network or to the Swift request environment.

The Swift Storlets repo provides:

* A Swift storlet middleware that can intercept a request for running a storlet over some data, 
  forward the data to the compute engine and stream back the compute engine results.
* A Storlet gateway API, defining the compute engine API used by the Swift storlet middleware
  to invoke computations.
* A StorletGateway implementation class that implements the StorletGateway API.
  This class runs in the context of the Swift storlet middleware inside the proxy and 
  object service pipelines, and is responsible  to communicate with the compute engine passing 
  it the data to be processed and getting back the result.
* The Docker based compute engine which is responsible for sandboxing the execution of the Storlet. 
  The Docker based compute engine is described in <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/docker_compute_engine.rst>
* Initial tools for managing and deploying Docker images within the Swift cluster.

The documentation in this repo is organized according to the various roles involved with Swift Storlets:

1. Storlet developer. The Storlet developer develops, packages and deploys Storlets to Swift. This is described in: <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/writing_and_deploying_storlets.rst>
2. Storlet user. A Swift user that wishes to invoke a deployed Storlet on some data object in Swift. <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/invoking_storlets.rst> describes how storlets can be invoked.
3. Storlets account manager (or account manager in short). The account manager is an admin user on the customer side who is typically the one responsible for paying the 
   bill (and perhaps setting ACLs). From Storlets perspective the account manager is responsible for managing the Docker image as well as the Storlets that can be executed 
   on data in the account. Part of the echo system is giving the account manager a way to deploy a Docker image to be used for Storlets execution within that account. 
   <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/building_and_deploying_docker_images.rst> has the details.
4. Swift Storlet manager. Typically, this is the Swift admin on the provider side that deals with rings and broken disks. 
   From the Storlets perspective (s)he is the one responsible for the below. <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/storlets_management.rst> has the details of the provided tools to do that.
   Those tools are installed on a designated node having a 'Storlet management' role (See installation section below)

  * Enabling a Swift account for Storlets. Since we wanted to give a self contained implementation we actuially give a tool for 
    creating a Storlet enabled account. That is, we first create a tenant and account in Keystone, and then do the Swift related
    operations for enabling the account for Storlets.
  * Deploy an account's Docker image across the cluster. This allows the account admin to upload a self tailored Docker image that the Swift admin can 
    then deploy across the cluster. Requests for running Storlets in that account would be served by Storlets running over this account's self tailored image.

5. Swift storlet developer. Someone looking at playing with the code of the storlet middleware and the storlet gateway. If you are one of those, you will be interested in:

  * <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/dev_and_test_guide.rst>
  * <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/storlets_docker_gateway.rst>

Finally, these are a MUST:

* <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/storlets_installation_guide.rst>
* <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/storlet_all_in_one.rst>

Installation
============
<https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/storlets_installation_guide.rst> describes how to install Storlets in an existing Swift cluster that uses Keystone.
For convenience we also provide a storlet all-in-one installation script that installs Swift with Keystone and Storlets in a single virtual machine.
See <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/storlets_all_in_one.rst>
The installation is based on Ansible and was tested on Ubuntu 14.10, and with Swift 1.13 and Swift 2.2.

Once installation is completed, you can try run the system tests as described in the <https://github.com/Open-I-Beam/swift-storlets/blob/master/doc/source/dev_and_test_guide.rst>
The system tests are a good reference for writing and deploying a Storlet.

Status
======
The purpose of this repository is to serve as a mostly read only reference for (1) the Swift storlets middleware, and (2) a storlets gateway 
implementaton.
Having said that we will be doing fixing of major bugs, potentially add some improvements and adaptations required to stay tuned with
the Swift Storlets middleware as it evolves while getting upstream.
Given enough interest from the community this status may change to be a more active project.

Acknowledgements
================

* The research leading to the development of this code received funding from the European Community's Seventh Framework Programme (FP7/2007-2013) under the grant agreements for the ENSURE and VISION Cloud projects.
* The development of this code received funding from the European Community's Seventh Framework Programme (FP7/2007-2013) under the grant agreements for the:

  * ForgetIT, where the code is used for pushing down analytics jobs to the object storage
  * COSMOS projects, where the code is used for TODO

* Future development of this code would receive funding from:

  * The European Community's Seventh Framework Programme (FP7/2007-2013) under the grant agreement for the FI-CORE project where the code is integrated with a holistic cloud deployment solution, and from
  * the European Community's Horizon 2020 (H2020/2014-2020) under the grant agreement for the IOStack project where the codeis used as a backend implementing Storage policies

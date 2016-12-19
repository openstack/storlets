Queriable "Secondary Storage" Data
==================================
It is said that the primary use case for object stores is to serve as secondary
storage. With the increasing amount of data being gathered and analysed
(have someone said IoT?) much of this data will make it to secondary storage.

Being kept on secondary storage does not mean that the data does not
need to be queriable anymore: A recent identified trend may be searched
for in older data that was moved to secondary storage. Storlets allow an
efficient and simple querying of data that resides in Swift.

Another closely related use case is that of aggregation. It is a well
known practice to aggregate data as it gets older. Storlets can serve
as 'in place' data aggregators.

Below are more concrete use cases that fall under the definition of
efficient queriable secondary storage data.

Pushing down SQL filtering from Spark
-------------------------------------
Apache Spark is a most popular analytics engine that has  multiple plugins for various types of analytics workloads.
In addition Spark can work with various backend storage systems, with Swift being one of them.
Spark SQL is a Spark plugin that allows to analyse structured data. At the heart of Spark SQL there is an SQL
engine called "Catalyst". Given an SQL query "Catalyst" identifies the filtering part of it. Thus, the filtering
part can be pushed down to a Storlet. The idea was presented in the Tokyo Openstack summit, and can
be viewed in [1]_.

Analysis over binary data
-------------------------
Analytics is typically done over textual data. In some cases that data is embedded in a
binary format. Storlets can be used to extract the textual data from the binary object, thus
saving the need to download it prior to extraction.
One such example is exif metadata in jpegs. This ideas was presented in the Paris Openstack summit,
and can be viewed in [2]_.

.. [1] https://www.youtube.com/watch?v=v9KCh--6Zw8
.. [2] https://www.youtube.com/watch?v=7tqMT0arV2k

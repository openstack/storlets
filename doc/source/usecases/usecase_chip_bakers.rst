The Chip Bakers Use Case
========================

At the heart of the chip bakers use case is the observation that it might be cheaper
to throw more processing power into the storage machines rather then invest in high
bandwidth pipes.

A concrete example of this use case is media processing in the cloud. Raw media files
are large and become even larger with the ongoing increase in resolution. processing
those file include various types of feature extraction, format transformation, and
metadata enrichment. Some elements of this processing is heavy on CPU, but perhaps
heavier in bandwidth.

This use case was presented in the Paris Openstack summit, and is featured as a super user
story that can be viewed in [1]_.

.. [1] http://superuser.openstack.org/articles/docker-meets-swift-a-broadcaster-s-experience

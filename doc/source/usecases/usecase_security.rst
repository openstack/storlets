Data Privacy
============

There are many use cases where it is worthwhile to share data that contain sensitive information,
once that information is obscured. Some examples are:

#. Medical records belonging to patients can be made available to researchers
   having the identity information obscured.
#. Financial transaction logs can be made available to analysis applications once the relevant
   identification information is obscured.
#. Smart electricity meters raw data can be made available to usage analysis
   applications if the data is being averaged. The raw data is sensitive as it can reveal
   e.g. the time at which the residents are at home.
#. Pictures of landscape having poeple in them can be made available to e.g. google earth
   if the faces are blurred.
#. 3D designs can be made available to manufacturers after a slicing lossy transformation.

Storlets can mask out the sensitive information without the data ever leaving the storage system.
A PoC if the concept was done in the context of the ForgetIT EU research project, and can be viewed
in [1]_

.. [1] https://www.youtube.com/watch?v=3rXeNbps8wo&t=105

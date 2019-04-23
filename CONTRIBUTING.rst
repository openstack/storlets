----------
Read First
----------
Pull requests submitted through GitHub will be ignored.

Bugs should be filed on Launchpad, not GitHub:

   https://bugs.launchpad.net/storlets

---------------------------------------------
Building changes off the upstream repository:
---------------------------------------------
This covers the scenario where you'd like to add / change code on the latest version of the storlet repo, do read the initial gerrit setup section if you haven't already done so.

* ``git clone https://github.com/openstack/storlets.git``

This will clone the upstream repo.

* ``cd ~/storlets``

Assuming you pulled down storlets to your home directory.

* ``git checkout -b <branch name>``

This will create a branch <branch name> for you to make changes in, gerrit uses the branch name as the topic field in the review page so make it meaningful.

* ``... makes code changes ...``
* ``git add <changed or new files / directories>``

Note that you can make any valid changes through GIT here (e.g. deleting a file).
When you're done with your set of changes and are ready to push them up to the storlets repository for review:

* ``git commit``

At this point you'll need to add a comment explaining the changes, an openstack standard here is to use one short sentence followed by an empty line and after a more lengthy explanation if required.

* ``git review``

This command will require no interaction and will push the change up to gerrit where it can be reviewed.

---------------------
Initial gerrit setup:
---------------------

This section covers one time steps required for setting up gerrit

Install gerrit (this varies depending on the OS but for example 'apt-get install git-review').
Setup the SSH keys through gerrit (i.e. https://review.opendev.org/#/settings/ssh-keys) you need to upload your public key from the system you plan to use for changes.

* ``git review -s``

This will verify gerrit can access the server using ssh.

* ``git config --global gitreview.username yourgerritusername``

Gerrit will usually prompt for your gerrit username if it mismatches from the current user on your system or you can hardcode it using the above (this is cleaner).

---------------------------------
Changes to an existing patch set:
---------------------------------

This section covers how to push changes to an existing patch set (e.g. you made a change and someone provided review comments you want to address).
Simply makes all the changes as you usually would usually the initial branch you used for the first patch set, after adding all the files to the local staging area and you are ready to commit:

* ``git commit --amend``

This appends on to the previous commit, gerrit uses an change-id it automatically adds to the commit message to associate patch sets on the server, if you are appending a change when you edit the commit message make sure not to change the change-id value otherwise gerrit will not associate the patch set with the original and create a brand new one.

* ``git review``

Note this command is the same even when appending a change.

---------
Rebasing:
---------

This section covers the various steps required when rebasing an existing local repo to the latest variant of storlets.
If you haven't made any changes yet (or made minor none conflicting ones) you can always run:

* ``git remote update``
* ``git checkout master``
* ``git pull --ff-only origin master``

This will essentially move up the HEAD of your local repo to point to the HEAD of master, but this will only be done if no merging is required, that is the fast forward option (for example you didn't change any files, or you didn't change any files that were changed on master since the last rebase).

Next switch to the branch you are trying to rebase and run:

* ``git checkout <branch you are trying to rebase>``
* ``git rebase master``

This will attempt to rebase by merging automatically but it may run into conflicts that you will need to manually resolve.
Such files will be listed and you will need to edit them. If you git diff the file it will resemble:

::

  <<<<<<< HEAD
  ... some change ...
  =======
  ... some other change ...
  >>>>>>> Title of change that introduced the above.

At this point you will need to resolve the conflict (by selecting one of the versions or a combination) and in so doing remove the added "<<<<<<<", "=======", and ">>>>>>>" text.
To complete the rebase after manually merging the file(s) issue:

* ``git rebase --continue``

After rebasing in any manner you may need to re-install storlets by going through the ansible script and building the various files.
If using TOX, you may need to re-create the TOX environment using the 'tox -r ...' command.

----------------
Weekly Meetings:
----------------
https://wiki.openstack.org/wiki/Meetings/Storlets

------------
IRC channel:
------------
#openstack-storlets at irc.freenode.net

=========
IRC Logs:
=========
http://eavesdrop.openstack.org/irclogs/%23openstack-storlets/

----------
Resources:
----------
https://docs.openstack.org/infra/manual/developers.html
https://docs.openstack.org/swift/latest/first_contribution_swift.html
https://docs.openstack.org/infra/manual/developers.html#development-workflow
https://docs.openstack.org/infra/manual/developers.html#development-workflow

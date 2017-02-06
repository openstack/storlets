Make sure to have a user that can sudo without a password.
With that user just do:

::

    sudo apt-get update
    sudo apt-get install python-tox python-nose git
    git clone https://github.com/openstack/storlets.git
    cd storlets
    ./s2aio.sh install

Test suite
==========

django-fab-deploy test suite executes fab commands against VirtualBox
virtual machines. Full test suite can take a very long time to run
(e.g. about 25 minutes for 4mbps broadband, the exact time depends heavily
on internet connection speed): all operations are really performed.

VM is rolled back to a clean state or an appropriate snapshot before each test.

This approach is quite extreme but I believe it's the only way to make sure
deployment system works: actually execute the deployment scripts against
concrete servers.

Preparations
------------

django-fab-deploy requires latest `fabtest`_ and `mock`_ packages
for running tests and (optionally) `coverage.py`_ for test coverage reports::

    pip install -U fabtest
    pip install 'mock==0.8'
    pip install coverage

Please follow `instructions <http://pypi.python.org/pypi/fabtest>`_ for
fabtest package in order to prepare OS image. django-fab-deploy tests
have 1 additional requirement: root user should have
'123' password (fabtest example VM images are configured this way).

.. _VirtualBox: http://www.virtualbox.org/
.. _fabtest: https://bitbucket.org/kmike/fabtest
.. _coverage.py: http://pypi.python.org/pypi/coverage
.. _mock: http://pypi.python.org/pypi/mock

Running tests
-------------

Pass VM name (e.g. Squeeze) to runtests.py script::

    cd fab_deploy_tests
    ./runtests.py <VM name or uid> <what to run>

<what to run> can be ``misc``, ``deploy``, ``all``, ``prepare`` or any
value acceptable by ``unittest.main()`` (e.g. a list of test cases).

Some tests require additional prepared snapshots in order to greatly speedup
test execution. But there is a chicken or the egg dilemma: these
snapshots can be only taken if software works fine for the VM (at least
tests are passed). So there is a very slow ``prepare`` test suite that ensures
preparing will work.

1. make sure slow tests are passing::

       ./runtests.py "VM_NAME" prepare

2. prepare snapshots::

       ./preparevm.py "VM_NAME"

3. tests can be run now::

       ./runtests.py "VM_NAME" all

.. note::

    Tests asking for user input (usually for password) should be considered
    failed. They mean django-fab-deploy was unable to properly setup
    server given the root ssh access.

.. note::

    Mercurial can't preserve 0600 file permissions and ssh is complaining
    if private key is 0644. So in order to run tests change
    permissions for the :file:`fab_deploy_tests\keys\id_rsa` to 0600::

        chmod 0600 fab_deploy_tests/keys/id_rsa

Coverage reports
----------------

In order to get coverage reports run::

    cd fab_deploy_tests
    ./runcoverage.sh <VM name or uid> <what to run>

html reports will be placed in ``htmlcov`` folder.

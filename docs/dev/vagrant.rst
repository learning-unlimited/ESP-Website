Vagrant based dev servers
=========================

.. contents:: :local:

Introduction
------------

Follow "Setup procedure" below to quickly install a dev server on your computer, regardless of what operating system you are using.  The procedure relies on Virtualbox, Vagrant and Fabric.  Your working copy is on your computer, but it is shared with a virtual machine (VM) which actually renders the site.

History
~~~~~~~

A dev server requires a lot of software components to run properly, and it would be time-consuming to set them up manually.  It is possible to make an automated (e.g. scripted) setup procedure, but it's not easy to support this capability on many different platforms.  Hence we support one platform (Ubuntu) and expect that developers use a virtual machine if Ubuntu is not their primary operating system.

For some time, we provided dev servers as Virtualbox images, which were prepared by (manually) creating a VM with Ubuntu installed, and then running our setup script inside the VM.  This worked well except that it was time-consuming to create these images (especially with chapter-specific databases and media files), and the files were very large (on the order of 5--10 GB) and time consuming to download.  That is what motivated the development of an alternative setup process, where the VM is created and prepared on your machine (with few manual steps).

With this new procedure, we should be able to standardize the platform that all development and production servers use (currently it's Ubuntu 14.04) without tying developers to that platform.

Setup procedure
---------------

Base components
~~~~~~~~~~~~~~~

This setup procedure does have some prerequisites of its own, which you will need to install according to your own platform:

* `Git <http://git-scm.com/downloads>`_
* `Virtualbox <https://www.virtualbox.org/wiki/Downloads>`_
* `Vagrant <http://www.vagrantup.com/downloads.html>`_
* `Python 2.7 <https://www.python.org/downloads/>`_
* Python libraries ``fabric`` and ``fabtools`` (can be installed using pip, which comes with Python)

If you are on a Linux system, it's likely that everything can be installed using a package manager on the command line, e.g. by running ``sudo apt-get install git virtualbox vagrant python2 python-pip && sudo pip install fabric fabtools``.

If you are on a Windows system, it's easiest if you install the `PyCrypto binaries <http://www.voidspace.org.uk/python/modules.shtml#pycrypto>`_ before trying to install Fabric. In addition, you may need to run ``setx path "%path%;C:\Python27;C:\Python27\Scripts;"`` in order to put ``python``, ``pip`` and ``fab`` on your PATH. Finally, you may find that the Git Bash shell does not interact well with Fabric. The Windows Command Prompt works much better.

Installation
~~~~~~~~~~~~

Using a shell, navigate to the directory where you would like to place the code (e.g. within your home directory), and check out our Git repository: ::

    git clone https://github.com/learning-unlimited/ESP-Website.git devsite
    cd devsite
    
If you already have a GitHub account with SSH keys set up, you may want to use ``git clone git@github.com:learning-unlimited/ESP-Website.git devsite`` to make it easy to push new code.

Next, use Vagrant to create your VM: ::

    vagrant up

Note that you will not be able to see the VM, since it runs in a "headless" mode by default.

The following command connects to the running VM and installs the software dependencies: ::

    fab setup

The development environment can be seeded with a database dump from an existing chapter, subject to a confidentiality agreement and security requirements on the part of the developer.  The ``loaddb`` task accepts an optional argument to load a database dump in .sql or any other Potgres-supported dump format. ::

    fab loaddb:/path/to/dump

Alternatively, database dumps can be downloaded automatically over HTTP. If you've been provided with a download URL, run: ::

    fab loaddb

Finally, you can set up your dev server with an empty database.  At some point during this process, you will be asked to enter information for the site's superuser account. ::

    fab emptydb

(If this step fails with an error "Operation now in progress", see the "Problems" section at the end.)

These commands can also be used on a system that has already been set up to bring your database up to date. They will overwrite the existing database on your dev server.

Now you can run the dev server: ::

    fab runserver

Once this is running, you should be able to open a Web browser on your computer (not within the VM) and navigate to http://localhost:8000, where you will see the site.

Usage
-----

The working copy you checked out with Git at the beginning contains the code you should use when working on the site.  It has been shared with the VM, and the VM does not have its own copy of the code.

If you need to debug things inside of the VM, you can open your shell, go to the directory where you checked out the code, and run ``vagrant ssh``.

* The location of the working copy within the VM is ``/home/vagrant/devsite``
* The location of the virtualenv used by the VM is ``/home/vagrant/venv``
  This is different from the conventional configuration (where the virtualenv is in an ``env`` directory within the working copy) so that the virtualenv is outside of the shared folder.  This is necessary to allow correct operation if the shared folders don't support symbolic links. The virtualenv is loaded automatically when you log in to the dev server.

Usual workflow
-----------------------------

Once you have everything set up, normal usage of your vagrant dev server should look something like this.

Before you start anything: ::

    vagrant up

To run your dev server: ::

    fab runserver

Other useful command examples: ::

    fab manage:shell_plus
    fab psql:"SELECT * FROM pg_stat_activity"

Once you're done: ::

    vagrant halt

One last command! When your devserver gets out of date, this command will update the dependencies, run migrations, and generally make things work again: ::

    fab refresh

If you want to add some custom shortcuts that don't need to go in the main fabfile, you can add them in a file called  ``local_fabfile.py`` in the same directory as ``fabfile.py``. Just add ``from fabfile import *`` at the top, and then write whatever commands you want.

For instructions on contributing changes and our ``git`` workflow, see `<contributing.rst>`_.

Problems
--------

1. The ``vagrant up`` command errors out with a Ruby stack trace.

    There is a `known issue <https://github.com/mitchellh/vagrant/issues/6748>`_ with Vagrant/VirtualBox on IPv6 static networking.

    One other quick thing to check is to open the VM directly from VirtualBox.  If it also fails,
    VirtualBox may give a more helpful error message. For example, if you have an older computer running a 32-bit operating system, then you
    might be out of luck since the VM runs 64-bit Ubuntu.  Similarly, on some computers you will need to enable hardware virtualization in the BIOS in order to run the 64-bit VM.

2. When running ``fab emptydb`` or ``fab loaddb``, it fails with an error "Operation now in progress" OR with error "error 47 from memcached_mget: SERVER HAS FAILED AND IS DISABLED UNTIL TIMED RETRY".

    You need to restart memcached.  First ssh into the VM with the command ``vagrant ssh``, then run

        ``sudo service memcached restart``

    Now try your ``fab`` command again.

3. I forgot the passphrase for the encrypted partition.

    You won't be able to recover the data, but you can start over by dropping the tablespace ``encrypted`` and then re-running ``fab setup``.

Some other common dev setup issues are discussed `here <https://github.com/learning-unlimited/ESP-Website/issues/1432>`_.

Creating a new dev VM
---------------------

Changes to the base VM should be needed very rarely, but you can't stay on the same Ubuntu version forever. Outline of steps used for the most recent upgrade:

1. Find a Vagrant .box file for Virtualbox with the version of Ubuntu that you want. You might do this by downloading a publicly available one or by running ``sudo do-release-upgrade`` from an older base VM. Be sure to start from a base VM, not your current dev server with a database on it.

2. Run ``esp/update_deps.sh`` on the VM from step 1. This isn't strictly required but will make dev setup easier in the future, especially dev setup testing.

3. Follow Vagrant's documentation to export the box you have to a .box file.

4. Upload the .box file to S3. If you don't have access, ask someone.

5. Update the Vagrantfile with the new VM's URL.

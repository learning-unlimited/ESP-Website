Vagrant based dev servers
=========================
Authors: 
   - Michael Price <price@learningu.org>

.. contents:: :local:

Introduction
------------

Follow "Setup procedure" below to quickly install a dev server on your computer, regardless of what operating system you are using.  The procedure relies on Virtualbox, Vagrant and Fabric.  Your working copy is on your computer, but it is shared with a virtual machine (VM) which actually renders the site.  

History
~~~~~~~

A dev server requires a lot of software components to run properly, and it would be time-consuming to set them up manually.  It is possible to make an automated (e.g. scripted) setup procedure, but it's not easy to support this capability on many different platforms.  Hence we support one platform (Ubuntu) and expect that developers use a virtual machine if Ubuntu is not their primary operating system.

For some time, we provided dev servers as Virtualbox images, which were prepared by (manually) creating a VM with Ubuntu installed, and then running our setup script inside the VM.  This worked well except that it was time-consuming to create these images (especially with chapter-specific databases and media files), and the files were very large (on the order of 5--10 GB) and time consuming to download.  That is what motivated the development of an alternative setup process, where the VM is created and prepared on your machine (with few manual steps).

With this new procedure, we should be able to standardize the platform that all development and production servers use (currently it's Ubuntu 12.04) without tying developers to that platform.

Setup procedure
---------------

Base components
~~~~~~~~~~~~~~~

This setup procedure does have some prerequisites of its own, which you will need to install according to your own platform:

* `Git <http://git-scm.com/downloads>`_
* `Virtualbox <https://www.virtualbox.org/wiki/Downloads>`_
* `Vagrant <http://www.vagrantup.com/downloads.html>`_
* `Python 2.7 <http://www.python.org/download/releases/2.7.6/>`_ and `pip <http://www.pip-installer.org/en/latest/installing.html>`_.
* Python libraries ``fabric`` and ``fabtools`` (can be installed using pip)

If you are on a Linux system, it's likely that everything except Vagrant and Virtualbox can be installed using a package manager on the command line.

Installation
~~~~~~~~~~~~

Using a shell, navigate to the directory where you would like to place the code (e.g. within your home directory), and check out our Git repository: ::

    git clone https://github.com/learning-unlimited/ESP-Website.git devsite
    cd devsite

Next, use Vagrant to create your VM: ::

    cd vagrant
    vagrant up

Note that you will not be able to see the VM, since it runs in a "headless" mode by default.

The following command connects to the running VM and installs the software dependencies: ::

    vagrant ssh -- -t -t -C "/home/vagrant/devsite/esp/update_deps.sh --virtualenv=/home/vagrant/devsite_virtualenv" 

Finally, you should use Fabric to deploy the development environment. At some point during this process, you will be asked to enter information for the site's superuser account. ::

    cd ../esp
    fab vagrant_dev_setup

The development environment can be seeded with a database dump from an existing chapter, subject to a confidentiality agreement and security requirements on the part of the developer.  The 'vagrant_dev_setup' task accepts optional arguments to load a database dump in .sql.gz or .sql.gz.gpg format: ::

    fab vagrant_dev_setup:dbuser=chaptername,dbfile=/path/to/chaptername.sql.gz.gpg

Typically the user name for the database is typically the lowercase name of the chapter; however, for MIT's system it is simply "esp".  Please ask the Web team for assistance if you need to know the user name, or obtain a database dump.

If you would like to load a database dump to a system that has already been set up, you may do so with the "load_db_dump" task (which overwrites the existing database on the dev server): ::

    fab load_db_dump:dbuser=chaptername,dbfile=/path/to/chaptername.sql.gz.gpg

Now you can run the dev server: ::

    fab run_devserver

Once this is running, you should be able to open a Web browser on your computer (not within the VM) and navigate to http://localhost:8000, where you will see the site.  

If you are using encrypted databases, you will need to run 'fab open_db' after each time you start the VM ('vagrant up'), and enter the passphrase that you specified during the setup process.

Usage
-----

The working copy you checked out with Git at the beginning contains the code you should use when working on the site.  It has been shared with the VM, and the VM does not have its own copy of the code.

If you need to debug things inside of the VM, you can go to the ``vagrant`` directory in your working copy and run ``vagrant ssh``. 

* The location of the working copy within the VM is ``/home/vagrant/devsite``
* The location of the virtualenv used by the VM is ``/home/vagrant/devsite_virtualenv``
  This is different from the conventional configuration (where the virtualenv is in an ``env`` directory within the working copy) so that the virtualenv is outside of the shared folder.  This is necessary to allow correct operation if the shared folders don't support symbolic links.
  
For example, if you want to run a shell: ::

    vagrant ssh
    source ~/devsite_virtualenv/bin/activate
    cd ~/devsite/esp
    ./manage.py shell_plus

An Apache2 server is also set up; you can access it from http://localhost:8080.  Note that whenever you change the code, you will need to run ``fab reload_apache`` to reload Apache2 inside the VM so that your changes take effect.

Usual workflow
-----------------------------

Once you have everything set up, normal usage of your vagrant dev server should look something like this.

Before you start anything: ::

    cd vagrant/
    vagrant up
    cd ../esp
    fab open_db

To run your dev server: ::

    fab run_devserver

Other useful command examples: ::

    fab manage:cmd=shell_plus
    fab manage:cmd='migrate program'

Once you're done: ::

    vagrant halt

Functionality that is lacking
-----------------------------

This is a TODO list for the developers:

* Support deploying to other targets (other than Vagrant VMs) - could be useful for deployment
* Make things more customizable
* Reduce number of setup steps


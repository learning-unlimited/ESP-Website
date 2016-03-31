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

With this new procedure, we should be able to standardize the platform that all development and production servers use (currently it's Ubuntu 12.04) without tying developers to that platform.

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

If you are on a Linux system, it's likely that everything except Vagrant and Virtualbox can be installed using a package manager on the command line.

If you are on a Windows system, it's easiest if you install the `PyCrypto binaries <http://www.voidspace.org.uk/python/modules.shtml#pycrypto>`_ before trying to install Fabric. In addition, you may need to run ``setx path "%path%;C:\Python27;C:\Python27\Scripts;"`` in order to put ``python``, ``pip`` and ``fab`` on your PATH. Finally, you may find that the Git Bash shell does not interact well with Fabric. The Windows Command Prompt works much better.

Installation
~~~~~~~~~~~~

Using a shell, navigate to the directory where you would like to place the code (e.g. within your home directory), and check out our Git repository: ::

    git clone https://github.com/learning-unlimited/ESP-Website.git devsite
    cd devsite

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

Using the PyCharm IDE
---------------------

The Professional Edition of PyCharm (unfortunately, not the free Community Edition) supports development and debugging of Django projects running in Vagrant.
Follow these steps to set it up for this project.  These instructions are for PyCharm version 2016.1.

1. Enable `Vagrant in PyCharm <https://www.jetbrains.com/help/pycharm/2016.1/vagrant.html>`_.

2. Enable `Django in PyCharm <https://www.jetbrains.com/help/pycharm/2016.1/django.html>`_.  The Django project root is the ``esp`` directory.  The Settings file is ``esp/settings.py``.

3. Set up a `remote Python interpreter <https://www.jetbrains.com/help/pycharm/2016.1/configuring-remote-interpreters-via-vagrant.html>`_. The "Python interpreter path" should be set to /home/vagrant/venv/bin/python .

4. Set up your run/debug configuration by going to Run -> Edit Configurations.  Add a configuration of type "Django Server".
    * Host: 0.0.0.0   Port: 8000
    * Environment variables:
        * DJANGO_SETTINGS_MODULE=esp.settings
        * VIRTUALENV=/home/vagrant/venv

To get started, first do ``vagrant up``, then ``fab runserver`` from a terminal, type in the passphrase for the encrypted partition, then Ctrl-C to exit the server.  You only
need to do these steps once per session (until you do ``vagrant halt``), so that the VM can access the encrypted partition.

Now you can start or stop the server using the Run, Debug, or Stop commands in the ``Run`` menu.  To debug your code, you can set whatever
breakpoints you want, and select Run -> Debug to run the server.  Go to localhost:8000 on your browser as usual, and the debugger will stop
on a breakpoint when it is hit.

If you forget to ``fab runserver`` after ``vagrant up``, then starting the server using the ``Run`` menu will not work because the encrypted partition will be inaccessible.

Problems
--------

1. The ``vagrant up`` command errors out with a Ruby stack trace.

    There is a `known issue <https://github.com/mitchellh/vagrant/issues/6748>`_ with Vagrant/VirtualBox on IPv6 static networking.

    One other quick thing to check is to open the VM directly from VirtualBox.  If it also fails,
    VirtualBox may give a more helpful error message. For example, if you have an older computer running a 32-bit operating system, then you
    might be out of luck since the VM runs 64-bit Ubuntu.

2. When running ``fab emptydb`` or ``fab loaddb``, it fails with an error "Operation now in progress".

    You need to restart memcached.  First ssh into the VM with the command ``vagrant ssh``, then run

        ``sudo service memcached restart``

    Now try your ``fab`` command again.

3. I forgot the passphrase for the encrypted partition.

    You won't be able to recover the data, but you can start over by dropping the tablespace ``encrypted`` and then re-running ``fab setup``.

Some other common dev setup issues are discussed `here <https://github.com/learning-unlimited/ESP-Website/issues/1432>`_.
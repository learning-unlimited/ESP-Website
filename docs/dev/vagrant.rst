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

With this new procedure, we should be able to standardize the platform that all development and production servers use (currently it's Ubuntu 22.04) without tying developers to that platform.

Setup procedure
---------------

Preparation
~~~~~~~~~~~

The site VM is 64-bit Ubuntu, so it will probably not work if your computer runs a 32-bit operating system, although such computers are rare nowadays.

On some computers, particularly Lenovo computers, you will need to enable hardware virtualization in the BIOS in order to run VMs. If you don't, this issue may manifest itself in Vagrant silently failing to boot your VM.

Base components
~~~~~~~~~~~~~~~

This setup procedure does have some prerequisites of its own, which you will need to install according to your own platform:

* `Git 2.43 <http://git-scm.com/downloads>`_
* `Virtualbox 7.0 <https://www.virtualbox.org/wiki/Downloads>`_ (and the accompanying Extension Pack; make sure it's the right version for your version of VirtualBox see, for example, https://forums.virtualbox.org/viewtopic.php?t=99355)
* `Vagrant 2.4.1 <http://www.vagrantup.com/downloads.html>`_ (make sure you install the 64-bit version)
* `Python 3.7+ <https://www.python.org/downloads/>`_
* Python libraries ``fabric`` and ``fabtools-python`` (can be installed using pip, which comes with Python; make sure to install version 1, not version 2 of fabric, so run ``pip install "fabric<2"``)

Take care with versions and consider using a virtual environment if you need multiple versions of Python.
You can always ask a member of the Web Team for help.

Installation
~~~~~~~~~~~~

Using a shell (such as Git Bash, which comes installed with Git), navigate to the directory where you would like to place the code (e.g., your home directory or desktop), and check out our Git repository: ::

    git clone https://github.com/learning-unlimited/ESP-Website.git devsite
    cd devsite

If you already have a GitHub account with SSH keys set up, you may want to use ``git clone git@github.com:learning-unlimited/ESP-Website.git devsite`` to make it easy to push new code.
If you already had vagrant installed, consider clearing your keys in ``~/.vagrant.d``.

Next, use Vagrant to create your VM: ::

    vagrant up

(If you get an error message suggesting that you run ``vagrant init``, you probably forgot to run ``cd devsite``.)

Note that you will not be able to see the VM, since it runs in a "headless" mode by default.

The following command connects to the running VM and installs the software dependencies: ::

    fab setup

If you are prompted for a password, try ``vagrant``. The development environment can be seeded with a database dump from an existing chapter, subject to a confidentiality agreement and security requirements on the part of the developer. (**NOTE:** Run **only one** of the next three commands. They are alternative ways to created the database.) If you have been provided with a download URL, run the following command. ::

    fab loaddb

You will be prompted to provide the URL. On future runs of ``fab loaddb``, the database will be automatically reloaded from this URL. (If you mistype the URL, you can edit it by ``vagrant ssh``-ing into the VM and editing ``/mnt/encrypted/fabric/dbconfig``.)

Alternatively, the ``loaddb`` task accepts an optional argument to load a database dump in .sql or any other Postgres-supported dump format. If you've acquired a database dump, you can load a database by running the following, replacing ``/path/to/dump`` with the path to your database dump: ::

    fab loaddb:/path/to/dump

Finally, you can set up your dev server with an empty database. At some point during this process, you will be asked to enter information for the site's superuser account. ::

    fab emptydb

(If this step fails with an error "Operation now in progress", see the `Problems section <#problems>`__ at the end.)

These commands can also be used on a system that has already been set up to bring your database up to date. They will overwrite the existing database on your dev server.

Now you can run the dev server: ::

    fab runserver

Once this is running, you should be able to open a web browser on your computer (not within the VM) and navigate to http://localhost:8000, where you will see the site.

Usage
-----

The working copy you checked out with Git at the beginning contains the code you should use when working on the site.  It has been shared with the VM, and the VM does not have its own copy of the code.

If you need to debug things inside of the VM, you can open your shell, go to the directory where you checked out the code, and run ``vagrant ssh``.

* The location of the working copy within the VM is ``/home/vagrant/devsite``
* The location of the virtualenv used by the VM is ``/home/vagrant/venv``
  This configuration is different from convention where the virtualenv is in an ``env`` directory within the working copy so that the virtualenv is outside of the shared folder.  This difference is necessary to allow correct operations if the shared folders don't support symbolic links. The virtualenv is loaded automatically when you log in to the dev server.

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

1. The ``vagrant up`` command errors out or times out while waiting for the VM to boot. (You may also want to investigate some of these for errors later in the process.)

    If it errors out with a Ruby stack trace, there is a `known issue <https://github.com/mitchellh/vagrant/issues/6748>`_ with Vagrant/VirtualBox on IPv6 static networking.

    One other thing to try is to run the VM not headlessly. You can run the VM directly from VirtualBox. You can also do this in Vagrant by uncommenting the line ``# vb.gui = true`` in ``Vagrantfile``, then running ``vagrant reload``. VirtualBox may give a more helpful error message, or you may be able to observe the VM getting stuck waiting for a keypress that never comes, say on the bootloader.

    * If you have an older computer running a 32-bit operating system, then you might be out of luck since the VM runs 64-bit Ubuntu. Also check that you didn't install the 32-bit version of Vagrant.
    * Check that hardware virtualization is enabled in your BIOS, particularly if you're running a Lenovo computer.


2. When running ``fab emptydb`` or ``fab loaddb``, it fails with an error ``Operation now in progress`` or with error ``Error 47 from memcached_mget: SERVER HAS FAILED AND IS DISABLED UNTIL TIMED RETRY``.

    You need to restart memcached.  First ssh into the VM with the command ``vagrant ssh``, then run

        ``sudo service memcached restart``

    Log out of the ssh session with ``exit``. Now try your ``fab`` command again.


3. I forgot the passphrase for the encrypted partition.

    You won't be able to recover the data, but you can start over by dropping the tablespace ``encrypted`` by running ``vagrant ssh`` then ``psql -c 'DROP TABLESPACE [ IF EXISTS ] encrypted'``. Now leave the VM by typing ``exit`` and re-run ``fab setup``.

Some other common dev setup issues are discussed `here <https://github.com/learning-unlimited/ESP-Website/issues/1432>`_.

Creating a new dev VM
---------------------

Changes to the base VM should be needed rarely, but you can't stay on the same Ubuntu version forever.
(Trust us; we've tried.)
Follow the following steps to upgrade the base VM for everyone to use.

1. From the ``devsite`` folder, destroy your existing virtual machine with ``vagrant destroy``.
(Make sure to save/commit any databases or configurations first!)
Clear Vagrant's caches by deleting the ``.vagrant.d`` directory (which will typically in your home folder.
This action will destroy all vagrant machines, so if you have others, just delete the one associated with your devsite.
Also delete the ``.vagrant`` directory in ``devsite/``.
Note: to get a head start on a slow step, start the download in step 5.ii then come back here.


2. 

	Download a new Ubuntu vagrant box by following steps i-iv below. Historically, we've used bento machines, which are browsable `here <https://app.vagrantup.com/boxes/search?utf8=%E2%9C%93&sort=downloads&provider=virtualbox&q=bento%2Fubuntu>`_.

	i. Make sure you have no local changes or commits on your branch.
	ii. Clone this repository into a folder called ``devsite``. Navigate to that folder in a terminal.
	iii. From your ``devsite`` folder, run ``rm Vagrantfile``.
	iv. Then run ``vagrant init bento/ubuntu-*``, but replace the asterisk with your desired version number. (Typically the most recent will be `XX.04` where the `XX` is the last two digits of the last even year.) If you choose to use something other than bento ubuntu, other steps in this process may require changes.

3. 

	Insert the line ``config.ssh.insert_key = false`` into the Vagrantfile after the ``config.vm.box`` line.
	(`See here <https://stackoverflow.com/a/28524909>`_ for an explanation.)


4. 

	Start the VM with ``vagrant up`` then SSH to the VM by running ``vagrant ssh``.
	You should not need a password to SSH in, but if it asks, try ``vagrant``.
	Then run the following code to install Python, pip, and friends as well as set the host name. Do not try to run it as a block (run one line at a time).::

		sudo add-apt-repository -y ppa:deadsnakes/ppa
		sudo apt update && sudo apt -y upgrade
		sudo apt install -y python3.7 python3.7-dev python3.7-distutils python3.7-venv
		curl https://bootstrap.pypa.io/pip/3.7/get-pip.py -o get-pip.py
		sudo python3.7 get-pip.py
		echo alias python=$(which python3.7) >> ~/.bashrc
		sudo hostnamectl set-hostname ludev
		chmod 755 /home/vagrant
		logout

5. 

	Create an encrypted partition. This step seems to change with the version of Ubuntu, so your mileage may vary here.
	See `this comment <https://github.com/learning-unlimited/ESP-Website/pull/3195#issue-785586914>`_ for instructions that worked on a different version, and search around (particularly https://askubuntu.com and https://devconnected.com/how-to-create-disk-partitions-on-linux/) for additional recommendations.

	i. Shut off the VM with ``vagrant halt``.

	ii. Download the Ubuntu install .iso here: https://ubuntu.com/download/desktop. Choose the version that matches your VM's.

	iii. Open VirtualBox, and click on the Vagrant VM that you just created.
	(It will probably be called something like ``devsite_default_`` followed by some numbers.)
	Then click on the "Settings" button, and click "Storage" on the left-hand menu.
	Next to "Controller: IDE Controller" line, click the "Adds optical drive" button (the icon looks like a blue circle with a green plus sign).
	Click the "Add" icon in the upper left, and browse to and select the ISO file you just downloaded.
	Then click "Choose" to close the pop-up window. Now click on the "System" tab on the left-hand menu, and move the "Optical" drive to the top of the "Boot Order" list by clicking it and clicking the up button.
	(Make sure the "Optical" drive has a checkmark). Finally, click "OK."

	iv. Run the virtual machine using the VirtualBox "Start" button, *not* by typing ``vagrant up`` in a terminal. If you are prompted, the username should be ubuntu with no password. If there is an popup prompting you to try or install Ubuntu, choose the "Try" option.

	v. Once the desktop comes up, open a terminal window (should be in "Applications" in the bottom left corner). Run the following commands to get the names of the volume group (VG) and logical volume (LV)::

		sudo apt update && sudo apt -y upgrade
		sudo apt install lvm2
		sudo lvs

	vi. Create space for an encrypted partition by running the following commands, replacing ``$VOLUME_GROUP`` and ``$LOGICAL_VOLUME`` with the names you found in the previous step. You may need to do ``e2fsck -f /dev/$VOLUME_GROUP/$LOGICAL_VOLUME`` first, but it should yell at you in that case. ::

		sudo lvreduce --resizefs --size -10G /dev/$VOLUME_GROUP/$LOGICAL_VOLUME
		sudo lvcreate -l 100%FREE -n keep_1 $VOLUME_GROUP
		exit

	vii. Close the VM by choosing "Close" from the File menu in the upper left then the "Power Off" option in the popup.
	
	viii. Open Settings again and change the Boot Order (in the System menu) so that the hard disk is above the optical disk. You can now close VirtualBox and delete the ISO file from your machine.

6. 

	Back in a terminal window in the ``devsite`` folder, run ``vagrant up``.
	Now SSH back into the machine from your shell (``vagrant ssh``) to install dev server dependencies.
	This step isn't strictly required but will make dev setup easier in the future, especially dev setup testing.
	If you get an error, you may not have set up the encrypted parition correctly. ::

		git clone https://github.com/learning-unlimited/ESP-Website.git
		cd ESP-Website/
		git checkout main
		esp/update_deps.sh
		cd ..
		rm -rf ESP-Website/
		logout

7. 

	Export the box you have to a .box file by running ``vagrant package --output ubuntu-*.box`` from your desktop terminal in ``devsite``, once again replacing the star with the correct version.

8. 

	Upload the .box file to the LU AWS S3 bucket.
	If you don't have access, ask someone on the LU Web Team.
	When you upload it, choose "Choose from predefined ACLs" and "Grant public-read access" under "Permissions" at the bottom.

9. 

	Restore the vagrantfile by running ``git restore Vagrantfile``, and update it so that ``config.vm.box`` matches the box name (probably ``'ubuntu-*'``) and ``config.vm.box_url`` points to the new VM's URL (which you can copy from AWS).
	Make sure to commit the changes in ``Vagrantfile`` to GitHub!

10. 

	Test that the new setup works.
	From the ``devsite/`` directory, run ``rm -rf ~/.vagrant.d/ && rm -rf .vagrant && vagrant destroy -f && vagrant up && fab setup && fab emptydb``.
	Again, this will remove other vagrant machines, so if you have others and know what you're doing, delete only the current one.

Upgrading your personal dev VM
------------------------------

If the base VM has been changed (see above), you will want to upgrade your development server. However, upgrading Ubuntu within a virtual machine can cause problems with your database. Therefore, you'll need to export your database, create a new virtual machine, then import your database:

1. Make a copy of `esp/esp/local_settings.py` somewhere with a different name (e.g., on your desktop as `old_local_settings.py`). The `local_settings.py` file will get overwritten by the end of this process and you will want to restore some of the settings from your previous VM setup.

2. From within the `devsite` folder, start your VM with ``vagrant up`` then run ``fab dumpdb``. This action will save your database as a dump file in the `devsite` folder called `devsite_django.sql`. You can also specify a filename if you would like with ``fab dumpdb:devsite_django.sql``.

3. Run ``vagrant destroy`` (note: this destroys your virtual machine. Only do it once you are sure your database has been backed up and you are ready to continue). 

4. Run ``git checkout main`` to check out the main branch. If you are upgrading your VM as part of a pull request, replace "main" with the name of the PR branch.

5. Before proceeding, double-check that you have all of the `required software <#base-components>`_ installed. Now follow the `VM installation instructions above <#installation>`_, starting at ``vagrant up``.
If you run into trouble, clear your SSH keys in ``~/.vagrant.d/`` and ``devsite/.vagrant``.
If you don't have other virtual machines, you can just delete both directories.

6. After running ``fab setup``, run ``fab loaddb:devsite_django.sql``. If you specified a different filename when you dumped your database, use that name instead.

7. Open your old local_settings.py file and your new local_settings.py file with a text editor. You will likely want to copy over most of your old local settings, but the new database password *must* remain (do not copy over the old one.

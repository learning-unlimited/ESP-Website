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

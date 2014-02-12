User Guide
==========

The basic workflow for setting up a new web site is
described in this guide. If this workflow doesn't fit for some reason then
django-fab-deploy can still be used as a collection of scripts, a lot of
them can be used independently.

Prerequisites
-------------

1. Clean Debian Lenny, Debian Squeeze, Ubuntu 10.04 or 10.10 server/VPS with
   root or sudo-enabled user ssh access;
2. working ssh key authentication;

.. warning::

    OpenVZ has serious issues with memory management
    (VIRT is counted and limited instead of RSS) so a lot of software
    (including apache2, Java and mysql's InnoDB engine) is nearly unusable on
    OpenVZ while being memory-wise and performant on XEN/KVM. So please try to
    avoid OpenVZ or Virtuozzo VPS's, use XEN or KVM or real servers.


Prepare the project
-------------------

1. Install django-fab-deploy its requirements::

       pip install django-fab-deploy
       pip install jinja2
       pip install "fabric >= 1.4"
       pip install fabric-taskset

2. Create :file:`fabfile.py` at project root. It should provide one or more
   function putting server details into Fabric environment. Otherwise it's just
   a standart Fabric's fabfile (e.g. project-specific scripts can also be put
   here). Example::

        # my_project/fabfile.py
        from fabric.api import env, task

        from fab_deploy.project import WebProject
        from fab_deploy.utils import update_env
        from fab_deploy.django import Django
        from fab_deploy.webserver.apache import Apache
        from fab_deploy.webserver.nginx import Nginx

        apps = dict(django=Django(Nginx(), Apache()))
        WebProject(apps=apps).expose_to_current_module()

        @task
        def my_site():
            env.hosts = ['my_site@example.com']
            env.conf = dict(
                DB_USER = 'my_site',
                DB_PASSWORD = 'password',
                DB_BACKEND = 'mysql',

                # uncomment this line if the project is not stored in VCS
                # default value is 'hg', 'git' is also supported
                # VCS = 'none',
            )
            update_env()

        my_site()

   ``apps`` dictionary is provided with default values for WebProject. Yes, 
   that is a fallback to previous versions of django-fab-deploy. And 
   there is a simpler syntax for the code above::

        from fab_deploy.project import WebProject
        from fab_deploy.utils import define_host

        WebProject().expose_to_current_module()

        @define_host('my_site@example.com')
        def my_site():
            return dict(
                DB_USER = 'my_site',
                DB_PASSWORD = 'password',
                DB_BACKEND = 'mysql',
            )

        my_site()

   In order to make things simple set the username in :attr:`env.hosts` string
   to your project name. It should be a valid python identifier.
   Don't worry if there is no such user on server, django-fab-deploy can
   create linux user and setup ssh access for you, and it is
   preferrable to have linux user per project if possible.

   .. note::

       There are some defaults, e.g. :attr:`DB_NAME <env.conf.DB_NAME>`
       equals to :attr:`INSTANCE_NAME <env.conf.INSTANCE_NAME>`,
       and :attr:`INSTANCE_NAME <env.conf.INSTANCE_NAME>` equals
       to username obtained from :attr:`env.hosts`.

       Read :doc:`fabfile` for more details.

3. Copy ``config_templates`` folder from django-fab-deploy to your project
   root, manually or by running the following command from the project root::

       django-fab-deploy config_templates

   Read the configs and adjust them if it is needed. Basic configs
   are usually a good starting point and should work as-is.

   .. note::

       {{ variables }} can be used in config templates (engine is jinja2).
       They will be replaced with values from :attr:`env.conf` on server.

       If you change web server config file or :attr:`env.conf` variables
       after initial deployment, apply the changes in web server configs
       by running ::

           fab update_web_servers

       It will update all remote configs of all apps of your default project.


4. Create :file:`config.server.py` near your project's ``settings.py``.
   This file will become :file:`config.py` on server. Example::

        # my_project/config.server.py
        # config file for environment-specific settings

        DEBUG = False
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': '{{ DB_NAME }}',
                'USER': '{{ DB_USER }}',
                'PASSWORD': '{{ DB_PASSWORD }}',
            }
        }

   Then create :file:`config.py` for local development.
   Import config in project's :file:`settings.py`::

       # Django settings for my_project project.
       # ...
       from config import *
       # ...

   ``config.py`` trick is also known as ``local_settings.py``
   (make sure ``config.py`` is ignored in your VCS if one is used).

   .. note::

       {{ variables }} can be used in :file:`config.server.py`. They will be
       replaced with values from :attr:`env.conf` on server.

       If you change :file:`config.server.py` or :attr:`env.conf` variables
       after initial deployment, apply the changes to :file:`config.server.py`
       by running ::

           fab apps.django.update_config

       for default apps configuration. Or more generic ::

           fab apps.{{ django_app_name }}.update_config

5. Create ``reqs`` folder at project root. This folder should contain
   text files with `pip requirements <http://pip.openplans.org/requirement-format.html>`_.

   You can get basic/example ``reqs`` folder by running ::

       django-fab-deploy example_reqs

   One file is special: :file:`reqs/all.txt`. This is the main requirements
   file. List all project requirements here one-by-one or (preferrable) by
   including other requirement files using "-r" syntax.

   There is also
   ::

       django-fab-deploy generate_reqs

   command. It creates ``reqs`` folder with :file:`all.txt` file containing
   a list of currently installed packages (obtained from ``pip freeze``).


The project should look like that after finishing steps 1-5::

    my_project
        ...
        config_templates <- this folder should be copied from django-fab-deploy
            apache.config
            django_wsgi.py
            hgrc
            nginx.config

        reqs             <- a folder with project's pip requirement files
            all.txt      <- main requirements file, list all requirements in this file
            active.txt   <- put recently modified requirements here
            ...          <- you can provide extra files and include them with '-r' syntax in e.g. all.txt

        config.py        <- this file should be included in settings.py and ignored in .hgignore
        config.server.py <- this is a production django config template (should be ignored too!)
        fabfile.py       <- your project's Fabric deployment script
        settings.py
        manage.py

.. note::

    django-fab-deploy does not enforce this layout; if it doesn't fit for some
    reason (e.g. you prefer single pip requirements file or django
    project in subfolder or you use django >= 1.4), take a
    look at :ref:`custom-project-layouts`.

The project is now ready to be deployed.

Prepare the server
------------------

.. note::

    It is assumed that you would manage imports in fabfile.py appropriately. E.g.
    for command "fab system.{{commmand}}" to work "from fab_deploy import system"
    would be added, for command "fab db.{{command}}" - "from fab_deploy import db",
    and so on.

1. If the server doesn't have sudo installed (e.g. clean Lenny or Squeezy)
   then install sudo on server::

       fab system.install_sudo

   .. note::

       Fabric commands should be executed in shell from the project root
       on local machine (not from the python console, not on server shell).

2. If there is no linux account for user specified in :attr:`env.hosts`
   then add a new linux server user, manually or using

   ::

       fab system.create_linux_account:"/home/kmike/.ssh/id_rsa.pub"

   You'll need the ssh public key.
   :func:`create_linux_account <fab_deploy.system.create_linux_account>`
   creates a new linux user and uploads provided ssh key. Test that ssh
   login is working::

       ssh my_site@example.com

   SSH keys for other developers can be added at any time::

       fab system.ssh_add_key:"/home/kmike/coworker-keys/ivan.id_dsa.pub"

3. Setup the database. django-fab-deploy can install mysql and create empty
   DB for the project (using defaults in your default host function)::

       fab db.mysql.install
       fab db.mysql.create_db

   :func:`mysql.install <fab_deploy.db.mysql.install>` does
   nothing if mysql is already installed on server. Otherwise it installs
   mysql-server package and set root password to
   :attr:`env.conf.DB_ROOT_PASSWORD`. If this option is empty, mysql_install
   will ask for a password.

   :func:`mysql.create_db <fab_deploy.db.mysql.create_db>` creates a new
   empty database named :attr:`env.conf.DB_NAME` (it equals to
   :attr:`env.conf.INSTANCE_NAME` by default, which equals to
   the user from :attr:`env.hosts` by default).
   :func:`mysql.create_db <fab_deploy.db.mysql.mysql.create_db>` will
   ask for a mysql root password if :attr:`DB_USER <env.conf.DB_USER>`
   is not 'root'.

   .. note::

        If the DB engine is not mysql then use appropriate commands.


4. If you feel brave you can now run ``fab full_deploy`` from the project root
   and get a working django site.

   .. warning::

      django-fab-deploy disables 'default' apache and nginx sites and
      takes over 'ports.conf' so apache is no longer listening to 80 port.

      If there are other sites on server (not managed by django-fab-deploy)
      they may become unaccessible due to these changes.

   ``fab full_deploy`` command:

   * installs necessary system and python packages;
   * configures web-servers for all applications of your project;
   * creates virtualenv;
   * uploads project to the server;
   * runs ``python manage.py syncdb`` and ``python manage.py migrate`` commands
     on server.

   Project sources will be available under ``~/src/<INSTANCE_NAME>``, virtualenv
   will be placed in ``~/envs/<INSTANCE_NAME>``.


Working with the server
-----------------------

django-fab-deploy provides additional commands that should be useful for
updating the server:

1. Source changes are deployed with :func:`fab_deploy.deploy.push` command::

       fab push

   Another example (deploy changes on 'prod' server, update pip
   requirements and perform migrations in one step::

       fab prod push:pip_update,migrate

2. Update web servers configuration::

       fab update_web_servers

3. Update some app configuration (:file:`config.server.py` for django 
   or :file:`production.ini` for pyramid)::

       fab apps.{{ app_name }}.update_config

   where ``app_name`` actually is a key in apps dictionary.

4. Requirements are updated with :func:`fab_deploy.virtualenv.pip_update`
   command. Update requirements listed in reqs/active.txt::

       fab update_r

   Update requirements listed in reqs/my_apps.txt::

       fab update_r:my_apps

5. Remotely change branch or revision (assuming :attr:`env.conf.VCS`
   is not 'none')::

       fab up:my_branch

Full list of commands can be found :doc:`here <reference>`.

:doc:`Customization guide <customization>` is also worth reading.

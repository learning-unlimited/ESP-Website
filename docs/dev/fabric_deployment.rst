Fabric Deployment
==============================
*Technical documentation*

Authors: 
   - Joel Legris <joel@aparat-tech.com>

.. contents:: :local:


Overview
--------

This document details the steps needed to setup and configure automated deployment of
the ESP web application using Fabric and a modified version of django-fab-deploy.
The fab script is currently capable of deploying a development ready configuration and the configuration should be considered experimental at this point because the project/file layout needed to be modified in order to accommodate some of the requirements of the fabric configuration

Notes on django-fab-deploy
--------------------------

The project uses a modified version of django-fab-deploy==0.7.5.
Changes were necessary to enable deployment on Ubuntu Server 12.04(from Ubuntu Server 10.04).
Furthermore, some modifications were made to the SQL statements that are issued during the
DB setup task in order to address a deployment failure that was occurring with the current version
of django-fab-deploy

Configuration Differences
-------------------------

django-fab-deploy does not support lighttpd at the moment but does configure nginx to function
as a front-end proxy to Apache.(This may be preferable). 

Installation Steps
------------------


ASSUMPTION: These steps are performed on a fresh installation of Ubuntu 12.04

Before proceeding with the installation, it is recommended that you first set up virtualenv
according to the instructions here:
http://www.virtualenv.org/

You will likely want to modify some of the default settings in the current fabfile.py to suit your local environment. These settings include:

- env.user
- env.password
- DB_PASSWORD
- DB_ROOT_PASSWORD 
- SUDO_USER

Activate your virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~

::

	source /pathtoenv/bin/activate

Install django-fab-deploy requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

	pip -r /projectpath/esp/lib/django-fab-deploy-ubuntu12-pgmods/requirements.txt

Install django-fab-deploy
~~~~~~~~~~~~~~~~~~~~~~~~~

::

	pip install -e /projectpath/esp/lib/django-fab-deploy-ubuntu12-pgmods/


Verify that django-fab-deploy is working
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

	fab -l

This command should display a list of available fabric tasks e.g:

::

	_make_clone                         Creates repository clone on remote server.
    deploy
    full_deploy                         Prepares server and deploys the project.
    install_databases                   Installs project's databases.
    install_r                           Installs pip requirements listed in ``<PIP_REQUIREMENTS_PATH>/<file>.txt`` file
    install_web_servers                 Installs servers for all of the project apps.
    production
    push                                Run it instead of your VCS push command.
    remove                              Shuts site down. This command doesn't clean everything, e.g.
    staging
    up                                  Runs vcs ``up`` or ``checkout`` command on server and reloads
    update_r                            Updates pip requirements listed in ``<PIP_REQUIREMENTS_PATH>/<file>.txt`` file
    update_web_servers
    apps.django.collectstatic
    apps.django.command_is_available
    apps.django.compress
    apps.django.deploy                  Deploys application on prepared server.
    apps.django.install_web_servers     Installs frontend and backend software.
 
    ...


Deploy the project!
~~~~~~~~~~~~~~~~~~~

Now that fabric and django-fab-deploy are configured, it's time to deploy the project:


- Setup Database

::

	fab db.postgres.create_user && db.postgres.create_db  

- Prepare full deployment of web server, virtualenv, sources, etc

:: 

    fab full_deploy

Assuming the full_deploy task completed without error. You should be able to the site running at : http://localhost  

Basic fab_deploy usage:
~~~~~~~~~~~~~~~~~~~~~~~

- restart apache

:: 
  
	fab apache_restart

- run migrations:

::

	fab migrate or fab migrate:users or fab migrate:programs

- push some code and redeploy

::

	fab push && fab update_django_config && fab migrate && fab apache_restart


To Be Continued.....


    



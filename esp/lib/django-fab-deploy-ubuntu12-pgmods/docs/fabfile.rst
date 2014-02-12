fabfile.py API
==============

Overview
--------

* Write a function populating :attr:`env.hosts` and :attr:`env.conf` for
  each server configuration.
* Call :func:`update_env() <fab_deploy.utils.update_env>` at the end of
  each function.
* It is possible to reduce boilerplate by using
  :func:`define_host <fab_deploy.utils.define_host>` decorator::

      from fab_deploy import *

      @define_host('my_site@example.com')
      def my_site():
          return {
              # ...
          }

* In order to specify configuration the fab commands should use, run the
  configuring function as a first fab command::

      fab my_site mysql_install

* In order to make configuration default call the configuring function at
  the end of :file:`fabfile.py`::

      from fab_deploy import *

      def my_site():
          env.hosts = ['my_site@example.com']
          env.conf = {
              # ...
          }
          # ...
          update_env()

      my_site()

  This way it'll be possible to run fab commands omitting the config name::

      fab mysql_install


Configuring
-----------

.. autofunction:: fab_deploy.utils.update_env


.. attribute:: env.hosts

    A list with host string. Example::

       env.hosts = ['user@example.com']

    See `fabric docs <http://docs.fabfile.org/1.0a/usage/execution.html#hosts>`_
    for explanation.

    User obtained from this string will be used for ssh logins and
    as a default value for :attr:`env.conf.INSTANCE_NAME`.

    .. note::

        multiple hosts are supported via multiple config functions, not
        via this option.

    .. warning::

        Due to bug in Fabric please don't use ``env.user`` and ``env.port``.
        Put the username and non-standard ssh port directly into host string.

.. attribute:: env.conf

    django-fab-deploy server configuration.

    All :attr:`env.conf` keys are available in config templates as
    jinja2 template variables.

.. attribute:: env.conf.INSTANCE_NAME

    Project instance name. It equals to username obtained from :attr:`env.hosts`
    by default. INSTANCE_NAME should be unique for server. If there are
    several sites running as one linux user, set different
    INSTANCE_NAMEs for them.

.. attribute:: env.conf.SERVER_NAME

    Site url for webserver configs. It equals to the first host from
    :attr:`env.hosts` by default.

.. attribute:: env.conf.DB_NAME

    Database name. It equals to :attr:`env.conf.INSTANCE_NAME` by default.

.. attribute:: env.conf.DB_USER

    Database user. It equals to 'root' by default.

.. attribute:: env.conf.DB_PASSWORD

    Database password.

.. attribute:: env.conf.DB_ROOT_PASSWORD

    Database password for a 'root' user. django-fab-deploy will ask for
    mysql root password when necessary if this option is not set.

.. attribute:: env.conf.SUDO_USER

    User with sudo privileges. It is 'root' by default.
    Use :func:`create_sudo_linux_account <fab_deploy.system.create_sudo_linux_account>`
    in order to create non-root sudoer.

.. attribute:: env.conf.PROCESSES

    The number of mod_wsgi daemon processes. It is a good idea to set it
    to number of processor cores + 1 for maximum performance or to 1 for
    minimal memory consumption. Default is 1.

.. attribute:: env.conf.THREADS

    The number of mod_wsgi threads per daemon process. Default is 15.

    .. note::

        Set :attr:`env.conf.THREADS` to 1 and :attr:`env.conf.PROCESSES` to
        a bigger number if your software is not thread-safe (it will
        consume more memory though).

.. attribute:: env.conf.OS

    A string with server operating system name. Set it to the correct value if
    autodetection fails for some reason. Supported operating systems:

    * lenny
    * squeeze
    * maverick

.. attribute:: env.conf.VCS

    The name of VCS the project is stored in. Supported values:

    * hg
    * git
    * none

    Default is 'hg'.

    VCS is used for making project clones and for pushing code updates.
    'none' VCS is able to upload tar.gz file with project sources
    on server via ssh and then extract it. Please prefer 'hg' or 'git'
    over 'none' if possible.

    One can write custom VCS module and set :attr:`env.conf.VCS` to
    its import path::

        env.conf = dict(
            # ...
            VCS = 'my_utils.my_vcs',
        )

    VCS module should provide 'init', 'up', 'push' and 'configure' functions.
    Look at :mod:`fab_deploy.vcs.hg` or :mod:`fab_deploy.vcs.none` for examples.

.. attribute:: env.conf.HG_BRANCH

    Named hg branch that should be active on server. Default is "default".
    This option can be used to have 1 repo with several named branches and
    run different servers from different branches.

.. attribute:: env.conf.GIT_BRANCH

    Git branch that should be active on server. Default is "master".
    This option can be used to run different servers from different git
    branches.

.. attribute:: env.conf.PROJECT_PATH

    Path to django project (relative to repo root). Default is ''.
    This should be set to a folder where project's manage.py reside.

.. attribute:: env.conf.LOCAL_CONFIG

    Local django config file name. Default is 'config.py'. Common values
    include 'local_settings.py' and 'settings_local.py'. This file should
    be placed inside :attr:`env.conf.PROJECT_PATH`, imported from settings.py
    and excluded from version control.

    .. note::

        Default value is not set to one of widely-used file names by default
        (e.g. 'local_settings.py') in order to prevent potential data loss
        during converting existing project to django-fab-deploy:
        this file is overwritten on server during deployment process; it is
        usually excluded from VCS and contains important information.

.. attribute:: env.conf.REMOTE_CONFIG_TEMPLATE

    The name of file with remote config template. Default is
    'config.server.py'. This file should be placed inside
    :attr:`env.conf.PROJECT_PATH`. It will become
    :attr:`env.conf.LOCAL_CONFIG` on server.

.. attribute:: env.conf.CONFIG_TEMPLATES_PATHS

    An iterable with paths to web server and other config templates.
    Default is ``['config_templates']``.

.. attribute:: env.conf.PIP_REQUIREMENTS_PATH

    Default is 'reqs'. This path is relative to repo root.

.. attribute:: env.conf.PIP_REQUIREMENTS

    The name of main requirements file. Requirements from it are installed
    during deployment. Default is 'all.txt'.

.. attribute:: env.conf.PIP_REQUIREMENTS_ACTIVE

    The name of pip requirements file with commonly updated requirements.
    Requirements from this file are updated by
    :func:`fab_deploy.virtualenv.pip_install` and
    :func:`fab_deploy.virtualenv.pip_update` commands when they are executed
    without arguments.

    ``fab push:pip_update`` command also updates only requirements listed here.

    Default is 'all.txt'.

You can put any other variables into the :attr:`env.conf`.
They will be accessible in config templates as template context variables.

Writing custom commands
-----------------------

While django-fab-deploy commands are just `Fabric <http://fabfile.org/>`_
commands, there are some helpers to make writing them easier.

.. autofunction:: fab_deploy.utils.inside_project

.. autofunction:: fab_deploy.utils.inside_src

.. autofunction:: fab_deploy.utils.run_as_sudo

.. autofunction:: fab_deploy.utils.define_host

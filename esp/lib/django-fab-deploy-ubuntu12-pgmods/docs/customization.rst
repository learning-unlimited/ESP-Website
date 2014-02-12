Customization
=============

.. _custom-deployment-scripts:

Custom deployment scripts
-------------------------

django-fab-deploy is intended to be a library, not a framework.
So the preferred way for customizing standard command is to just
wrap it or to create a new command by combining existing commands::

    # fabfile.py
    from fab_deploy import *
    from fab_deploy.utils import run_as_sudo
    import fab_deploy.deploy

    @run_as_sudo
    def install_java():
        run('aptitude update')
        run('aptitude install -y default-jre')

    def full_deploy():
        install_java()
        fab_deploy.deploy.full_deploy()


:func:`fab_deploy.deploy.push` accepts callable 'before_restart'
keyword argument. This callable will be executed after code uploading
but before the web server reloads the code.

.. _fab-push-customization:

An example of 'fab push' customization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    # fabfile.py
    from fab_deploy import *
    import fab_deploy.deploy

    @inside_src
    def rebuild_docs():
        with cd('docs'):
            run ('rm -rf ./_build')
            run('make html > /dev/null')

    def push(*args):

        # run local tests before pushing
        local('./runtests.sh')

        # rebuild static files before restarting the web server
        def before_restart():
            manage('collectstatic --noinput')
            manage('assets rebuild')

        # execute default push command
        fab_deploy.deploy.push(*args, before_restart=before_restart)

        # rebuild developer documentation after pushing
        rebuild_docs()


.. _custom-project-layouts:

Custom project layouts
----------------------

:doc:`guide` describes standard project layout::

    my_project
        ...
        config_templates <- this folder should be copied from django-fab-deploy
            ...

        reqs             <- a folder with project's pip requirement files
            all.txt      <- main requirements file, list all requirements in this file
            active.txt   <- put recently modified requirements here
            ...          <- you can provide extra files and include them with '-r' syntax in e.g. all.txt

        config.py        <- this file should be included in settings.py and ignored in .hgignore
        config.server.py <- this is a production django config template
        fabfile.py       <- your project's Fabric deployment script
        settings.py
        manage.py

django-fab-deploy does not enforce this layout. Requirements handling,
config templates placement, local settings file names and project source
folder can be customized using these options:

* :attr:`env.conf.PROJECT_PATH`
* :attr:`env.conf.LOCAL_CONFIG`
* :attr:`env.conf.REMOTE_CONFIG_TEMPLATE`
* :attr:`env.conf.CONFIG_TEMPLATES_PATHS`
* :attr:`env.conf.PIP_REQUIREMENTS_PATH`
* :attr:`env.conf.PIP_REQUIREMENTS`
* :attr:`env.conf.PIP_REQUIREMENTS_ACTIVE`

Example
~~~~~~~

Let's configure django-fab-deploy to use the following layout::

    my_project
        hosting                 <- a folder with server configs
            staging             <- custom configs for 'staging' server
                apache.config   <- custom apache config for staging server

            production          <- custom configs for 'production' server
                apache.config
                nginx.config

            apache.config       <- default configs
            django_wsgi.py
            nginx.config

        src                     <- django project source files
            apps
                ...

            local_settings.py   <- local settings
            stage_settings.py   <- local settings for staging server
            prod_settings.py    <- local settings for production server

            settings.py
            manage.py

        requirements.txt        <- single file with all pip requirements
        fabfile.py              <- project's Fabric deployment script

It uses subfolder for storing django project sources, single pip requirements
file and different config templates for different servers in
non-default locations.

fabfile.py::

    from fab_deploy.utils import define_host

    # Common layout options.
    # They are separated in this example in order to stay DRY.
    COMMON_OPTIONS = dict(
        PROJECT_PATH = 'src',
        LOCAL_CONFIG = 'local_settings.py',
        PIP_REQUIREMENTS = 'requirements.txt',
        PIP_REQUIREMENTS_ACTIVE = 'requirements.txt',
        PIP_REQUIREMENTS_PATH = '',
    )

    @define_host('user@staging.example.com', COMMON_OPTIONS)
    def staging():
        return dict(
            REMOTE_CONFIG_TEMPLATE = 'stage_settings.py',
            CONFIG_TEMPLATES_PATHS = ['hosting/staging', 'hosting'],
        )

    @define_host('user@example.com', COMMON_OPTIONS)
    def production():
        return dict(
            REMOTE_CONFIG_TEMPLATE = 'prod_settings.py',
            CONFIG_TEMPLATES_PATHS = ['hosting/production', 'hosting'],
        )


Example 2: django 1.4 layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Django 1.4 presents a new project layout. It can be used e.g. this way::

    my_project
        my_project
            config_templates
                ...
            reqs
                ...
            ...
            config.py
            config.server.py
            settings.py

        fabfile.py
        manage.py
        ...

fabfile.py::

    from fab_deploy.utils import define_host

    @define_host('user@example.com')
    def staging():
        return dict(
            CONFIG_TEMPLATES_PATHS=['my_project/config_templates'],
            LOCAL_CONFIG = 'my_project/config.py',
            REMOTE_CONFIG_TEMPLATE = 'my_project/config.server.py',
            PIP_REQUIREMENTS_PATH = 'my_project/reqs/',
        )

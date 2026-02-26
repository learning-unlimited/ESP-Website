Docker based dev servers
========================

.. contents:: :local:

Introduction
------------

Follow the steps below to quickly set up a local development server using Docker.
This approach requires **only Docker and Docker Compose** to be installed — no
other host dependencies or specific Python versions needed.

The Docker setup runs three containers:

- **web**: The Django application (Python 3.7)
- **db**: PostgreSQL 14 database
- **memcached**: Memcached caching layer

Your working copy is mounted into the container, so you can edit code with your
preferred editor on your host machine and see changes reflected immediately.

Prerequisites
-------------

**Windows and macOS:**

Install `Docker Desktop <https://docs.docker.com/desktop/>`_, which includes
Docker Engine and Docker Compose in a single installer.

**Linux:**

Install `Docker Engine <https://docs.docker.com/engine/install/>`_ and the
`Docker Compose plugin <https://docs.docker.com/compose/install/linux/>`_
separately (or install Docker Desktop for Linux if you prefer a GUI).

That's it! No Python, Node.js, PostgreSQL, or any other dependency needs to be
installed on your host machine.

Quick Start
-----------

1. Clone the repository::

    git clone https://github.com/learning-unlimited/ESP-Website.git devsite
    cd devsite

   If you have SSH keys set up::

    git clone git@github.com:learning-unlimited/ESP-Website.git devsite
    cd devsite

2. Build and start all services::

    docker compose up --build

   The first build will take several minutes as it installs system and Python
   dependencies. Subsequent starts will be much faster due to Docker layer caching.

3. The entrypoint script will automatically (on first run):

   - Create ``local_settings.py`` from the Docker template (if it doesn't exist)
   - Create media symlinks (``images``, ``styles``)
   - Wait for PostgreSQL to be ready
   - Run database migrations
   - Collect static files

   On subsequent runs, migrations and static file collection are skipped for
   faster startup. To force them to run again (e.g., after pulling new code)::

    FORCE_SETUP=1 docker compose up

4. Once you see ``Starting development server at http://0.0.0.0:8000/``,
   open your browser and navigate to http://localhost:8000.

5. To create an admin account, open a new terminal and run::

    docker compose exec web python esp/manage.py createsuperuser

Stopping & Starting
--------------------

To stop the containers::

    docker compose down

To stop and **delete the database** (fresh start)::

    docker compose down -v

To start again (no rebuild needed unless you changed the Dockerfile)::

    docker compose up

To rebuild after changing the Dockerfile or requirements.txt::

    docker compose down
    docker compose up --build

.. note::
   Always run ``docker compose down`` before ``docker compose up --build`` to
   avoid build errors caused by symlinks in the mounted volume.

Common Commands
---------------

Run any ``manage.py`` command::

    docker compose exec web python esp/manage.py <command>

Examples::

    # Open a Django shell
    docker compose exec web python esp/manage.py shell_plus

    # Run migrations
    docker compose exec web python esp/manage.py migrate

    # Run tests
    docker compose exec web python esp/manage.py test

    # Open a bash shell inside the container
    docker compose exec web bash

    # Connect to the PostgreSQL database
    docker compose exec db psql -U esp devsite_django

Loading a Database Dump
-----------------------

If you have an existing database dump (e.g., from a previous development setup),
you can load it into the Docker environment.

**Step 1: Start with a clean database** by removing the existing volume and
bringing the containers back up::

    docker compose down -v
    docker compose up

   Wait a few seconds for PostgreSQL to initialize, then proceed.

**Step 2: Copy the dump into the container.**

On Linux / macOS / WSL::

    docker cp /path/to/dump.sql $(docker compose ps -q db):/tmp/dump.sql

On Windows PowerShell, run the two commands separately::

    # First, get the container ID
    docker compose ps -q db
    # Then copy, replacing <container-id> with the output above
    docker cp C:\path\to\dump.sql <container-id>:/tmp/dump.sql

**Step 3: Load the dump.**

For a plain SQL dump (``.sql`` file)::

    docker compose exec db psql -U esp devsite_django -f /tmp/dump.sql

For a custom-format dump (created with ``pg_dump -Fc``)::

    docker compose exec db pg_restore --verbose --dbname=devsite_django \
        --no-owner --no-acl -U esp /tmp/dump.sql

**Step 4: Re-run migrations** to ensure the schema matches the current code::

    docker compose exec web python esp/manage.py migrate

.. note::
   If you see ownership or permission errors when loading a dump from a different
   environment, the ``--no-owner --no-acl`` flags on ``pg_restore`` will
   ignore those. For plain SQL dumps, you can safely ignore ``ALTER OWNER``
   errors — the data will still load correctly.

Configuration
-------------

The Docker setup uses ``esp/esp/local_settings.py.docker`` as the template for
``local_settings.py``. It is automatically copied on first run. If you need to
customize settings:

1. Edit ``esp/esp/local_settings.py`` directly (it is gitignored)
2. Or edit ``esp/esp/local_settings.py.docker`` to change the defaults for all
   Docker users

- ``DATABASES['default']['HOST']`` is ``'db'`` (the Docker service name) instead of
  ``'localhost'``
- ``CACHES['default']['LOCATION']`` is ``'memcached:11211'`` instead of
  ``'127.0.0.1:11211'``
- ``ALLOWED_HOSTS`` is ``['*']`` for convenience in local development

Troubleshooting
---------------

1. **Port already in use**

   If port 8000 (or 5432 or 11211) is in use, either stop the conflicting service
   or change the port mapping in ``docker-compose.yml``, e.g.::

       ports:
         - "9000:8000"

2. **Database connection errors**

   The entrypoint script waits for PostgreSQL to be ready, but if you still see
   connection errors, try::

       docker compose restart web

3. **Permission issues with mounted volumes**

   On Linux, files created inside the container may be owned by root. Fix with::

       sudo chown -R $USER:$USER .

4. **Stale containers**

   If things seem broken after a ``git pull``, try a clean rebuild::

       docker compose down -v
       FORCE_SETUP=1 docker compose up --build

5. **Build fails with "invalid file request"**

   If you see an error like ``invalid file request esp/public/media/images``
   during ``docker compose build``, run ``docker compose down`` first to remove
   the symlinks created by the entrypoint, then rebuild::

       docker compose down
       docker compose up --build

6. **Docker Desktop is not running (Windows / macOS)**

   *Windows error:* ``unable to get image … open //./pipe/dockerDesktopLinuxEngine:
   The system cannot find the file specified.``

   *macOS error:* ``Cannot connect to the Docker daemon at
   unix:///var/run/docker.sock. Is the docker daemon running?``

   Both errors mean Docker Desktop is not running. Open **Docker Desktop** and
   wait until the icon in the system tray (Windows) or menu bar (macOS) shows
   it is ready. You can verify by running::

       docker info

   If this returns engine details without errors, retry
   ``docker compose up --build``.

   *Windows only:* if the issue persists, open
   **Docker Desktop → Settings → General** and ensure
   **"Use the WSL 2 based engine"** is checked, then click **Apply & Restart**.

Docker based dev setup
======================

.. contents:: :local:

Introduction
------------

This setup provides a Docker-based alternative to the Vagrant workflow for local
development. It is especially useful on macOS Apple Silicon systems where
``vagrant_utm`` has known reliability issues with Vagrant 2.4.x.

Prerequisites
-------------

Install:

* Docker Desktop (or Docker Engine + Compose plugin)
* Git

Quick start
-----------

From the repository root, build and start all services: ::

    docker compose up --build -d

Run database migrations: ::

    docker compose run --rm web python manage.py migrate

Create a superuser (optional): ::

    docker compose run --rm web python manage.py createsuperuser

Run the development server (foreground): ::

    docker compose up web

Then open http://localhost:8000.

Contributor command reference
-----------------------------

Most day-to-day commands can be run as follows: ::

    # Apply migrations after pulling changes
    docker compose run --rm web python manage.py migrate

    # Start the dev server
    docker compose up web

    # Run an arbitrary Django management command
    docker compose run --rm web python manage.py <command>

    # Run the test suite
    docker compose run --rm web python manage.py test

What the compose stack includes
-------------------------------

* ``web``: Django app container
* ``db``: PostgreSQL database
* ``memcached``: Cache backend

The repository is bind-mounted into ``/workspace`` inside the ``web`` container,
so code edits on your host are reflected immediately.

Notes
-----

* On first boot, ``docker/entrypoint.sh`` creates ``esp/esp/local_settings.py``
  from ``docker/local_settings.py`` if it is missing.
* Existing Vagrant/Fabric commands remain supported; this is an additional
  development path, not a replacement.
* To run management commands, use ``docker compose run --rm web ...``.

Stopping and cleanup
--------------------

Stop services: ::

    docker compose down

Remove containers and the database volume: ::

    docker compose down -v

django-fab-deploy documentation
===============================

django-fab-deploy is a collection of `fabric`_ scripts for deploying and
managing django projects on Debian/Ubuntu servers.

Design goals
------------

* Provide (heroku, ep.io, gondor.io, ...)-like experience using
  your own VPS/server;
* servers should be configured in most standard and obvious
  way: invent as little as possible;
* developer should be able to customize deployment;
* it should be possible to integrate django-fab-deploy into existing projects;
* try to be a library, not a framework; parts of django-fab-deploy
  should be usable separately.

Tech overview
-------------

* django projects are isolated with `virtualenv`_ and
  (optionally) linux and db users;
* python requirements are managed using `pip`_;
* server interactions are automated and repeatable
  (the tool is `fabric`_);
* several projects can be deployed on the same VPS;
* one project can be deployed on several servers.

Server software:

* First-class support: Debian Squeeze, Ubuntu 10.04 LTS;
* also supported: Debian Lenny, Ubuntu 10.10;
* the project is deployed with `Apache`_ + `mod_wsgi`_ for backend and
  `nginx`_ in front as a reverse proxy;
* DB: MySQL and PostgreSQL (+PostGIS) support is provided out of box;
* VCS: hg and git support is provided out of box + it is possible not
  to store project into VCS.


.. _virtualenv: http://virtualenv.openplans.org/
.. _pip: http://pip.openplans.org/
.. _fabric: http://fabfile.org/
.. _Apache: http://httpd.apache.org/
.. _mod_wsgi: http://code.google.com/p/modwsgi/
.. _nginx: http://nginx.org/

.. toctree::
   :maxdepth: 2

   guide
   customization
   fabfile
   reference
   testing
   related

Make sure you've read the following document if you are upgrading from
previous versions of django-fab-deploy:

.. toctree::
   :maxdepth: 1

   CHANGES

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://bitbucket.org/kmike/django-fab-deploy/issues/new

Contributing
============

Development of django-fab-deploy happens at Bitbucket:
https://bitbucket.org/kmike/django-fab-deploy/

You are highly encouraged to participate in the development of
django-fab-deploy. If you don’t like Bitbucket or Mercurial (for some reason)
you’re welcome to send regular patches.

.. toctree::
   :maxdepth: 1

   AUTHORS

License
=======

Licensed under a MIT license.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

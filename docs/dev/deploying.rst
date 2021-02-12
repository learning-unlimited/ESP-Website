Deploying to production
=======================

Deploying a new site
--------------------

To deploy a new site, first make sure you know:

#. the hostname the chapter prefers
#. the chapter's contact email address
#. the group's name (e.g. "MIT ESP" or "Yale Splash")
#. the chapter's preferred `theme <../admin/available_themes.rst>`_

Then ssh to ``diogenes``, grab the latest version of
``deploy/server_setup/new_site.sh``, ``cd`` to ``/lu/sites``, and
run ``sudo new_site.sh --all``.  If the directory already exists for the
chapter, you may wish to delete it to get a clean start.  (You may instead
clone the repository yourself, ``cd`` into it, and run the script from there.)
Follow the instructions to set up the site.  For the site directory name,
choose something short that's likely to stay unique and understandable as we
add more chapters.  When it does the "create superuser", you should create
yourself an account; afterwards chapter admins can create their own accounts
and you can make them admins.

If something doesn't work, and you need to re-run a particular step, you can do
so by passing the appropriate flag to ``new_site.sh``.  Note that some steps
won't work if you run them twice, so if a step fails partway through you may
need to complete or undo it manually.  The script will remember your settings;
you just need to tell it the same directory again.

It can also be helpful to run ``python manage.py migrate`` if the setup fails
during the database or settings phase.

Finally, email the chapter to let them know that you've set up their site, and
with instructions to set up their accounts, whatever parts of their theme you
didn't set up.  You can also point them at the documentation in the repository
and on the LU wiki and at websupport.

Deactivating a site
-------------------

To deactivate a site, simply remove or comment out its lines in
``/etc/apache2/sites-available/esp_sites.conf``, ``/etc/crontab``, and
``/etc/exim4/update-exim4.conf.conf``, and move its site directory to
``/lu/sites/inactive``.

TODO(benkraft): write a quick script for this.

Setting up a new server
-----------------------

TODO

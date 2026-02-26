============================================
 ESP Website Stable Release 05 release notes
============================================

.. contents:: :local:

Changelog
=========

Stripe credit card module
~~~~~~~~~~~~~~~~~~~~~~~~~

LU is switching credit card processors from First Data to Stripe; Stripe offers a
more modern API, and also does not charge monthly fees.

The front-end of this module is similar to the other credit card modules.
The STRIPE_CONFIG settings should be configured for the module to interact with
Stripe API servers.

For more information on usage, see
`</docs/admin/program_modules.rst#stripe-credit-card-module>`_.

Group texting with Twilio
~~~~~~~~~~~~~~~~~~~~~~~~~

The new Twilio group texting module enables mass texting messages to users who
have opted to receive text messages, under the same filtering constraints
available in the email communications panel. Currently the only supported
back-end is Twilio, so a Twilio account is needed and Twilio configuration
options need to be set.

We expect that this will be primarily used for emergency notification situations.

For more information on usage, see
`</docs/admin/program_modules.rst#group-text-module>`_.

Student applications module
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some programs may want to run admissions and have students apply for enrollment
to specific classes.  The new application system provides functionality for
program and class-specific applications, teacher review of applicants, admin
review of applicants, and admin admissions management. For more information,
see `</docs/admin/student_apps.rst>`_.

Improvements to the onsite class changes grid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There have been various improvements to the class changes grid, including:

- Enrolled classes will always be displayed, even if their categories are
  hidden.

- It is possible to show all / hide all categories at once, without manually
  toggling all categories.

- Timeblocks that have already occured can be hidden from the page, so that the
  timeblock on the left is the current or upcoming timeblock.

Donation module
~~~~~~~~~~~~~~~

This program module can be used to solicit donations for Learning Unlimited. If
this module is enabled, students who visit the page can, if they so choose,
select one of a few donation options (and those options are admin
configurable). Asking for donations from parents and students can be a good way
to help fundraise for LU community events, chapter services, and operational
costs. If you are interested in fundraising this way, get in contact with an LU
volunteer.

For more information on configuring and using the module, see
`</docs/admin/program_modules.rst#donation-module>`_.

Improvements to scheduling checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some improvements were made to the scheduling checks page, including:

- a new "missing resources by hour" check

- timeblock information in the "classes missing resources" and "wrong classroom
  type" checks

- counts in the "admins teaching per timeslot" check

Additionally, for larger chapters the page may take a long time to load.  More
improvements are in the works, but for now, the page
<site>.learningu.org/manage/<program>/<instance>/scheduling_check_list
will display a list of links to display the checks individually; most will load
much more quickly than the entire page.


Deadline for walk-in activities / open classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is now possible to set a deadline for open class (a.k.a. walk-in activity)
registration separately from that of normal teacher registration.

- To set the registration deadline for open class registration only, create a
  deadline with the "Create open classes" permission type.

- To set the registration deadline for normal teacher registration only, create
  a deadline with the "Create standard classes" permission type.

- To set the registration deadline for all types of teacher registration,
  create a deadline with the "Create classes of all types" permission type.
  This is the same as the previously used teacher registration deadline, so any
  registrations that have already been set up do not need any updating.

NOTE: For more information on open classes, see the "Open classes" section of
the previous release notes: `</docs/admin/releases/04/README.rst>`_.  The open
classes feature is disabled by default.  And when it is disabled, you can
safely use either the "Create standard classes" or
"Create classes of all types" deadlines, without accidentally opening
registration for open classes.

Custom Javascript
~~~~~~~~~~~~~~~~~

ADDITIONAL_TEMPLATE_SCRIPTS in local_settings.py can be configured to add
arbitrary HTML code to the bottom of every page. The intended use case is for
including JavaScript for analytics or similar tools.

Teacher bio privacy setting
~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is now possible for teachers to make their biographies private, so that no
non-admins can see their biography or list of past classes. To hide their
biography, a teacher needs to edit their teacher biography
(/teach/teachers/<username>/bio.edit.html), check the box "Hide your teacher
biography", and then clicking "Save" at the bottom. Admins can also do this via
morphing, or by finding the correct TeacherBio (at /admin/program/teacherbio/),
checking the "Hidden" box, and then clicking "Save" at the bottom.

Class flags improvements
~~~~~~~~~~~~~~~~~~~~~~~~

- Several bugs fixed, and performance improvements.

- The flag query builder now has more filters, including flag
  creation/modification time and class scheduling status.

- The teacher check-in page now shows more information about a class, including
  its flags.

Minor feature additions and bugfixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Some dashboard display improvements.

- Many small improvements to the admin panel, for better displaying,
  filtering, and searching.

- The "Administer" permission, when granted without a program being
  specified, now correctly implies the "Administer" permission on all
  programs.

- New "cancel registration" deadline can be set to specify when students are
  allowed to cancel their registrations themselves.

- New "Teacher training signup" deadline can be set to specify when teachers
  are allowed to sign up for teacher training.

- When a teacher modifies a class, the class comments email will have a
  subject line that starts with "Re:".  This makes it clearer when new
  classes are being registered versus when existing classes are being
  edited.

- By default, static QSD pages list the last modification time, as well as
  the username of the user who last modified the page.  To hide the username
  on all pages, go to /admin/tagdict/tag/ and set a Tag with key
  ``qsd_display_date_author`` and value ``Date``.  To hide the username and
  modification time, set the value as ``None``. Note that these changes
  only appear to non-administrator users; administrators will still
  be able to see both the time and user.

- Improvements to the student extra/optional costs module now allow
  equally-priced options, such as lunch or t-shirt options, to be used in
  the form.

- Improvements to the user search controller now make it sometimes possible
  to combine filters and not incorrectly get 0 results.

- After searching for a teacher and going to their userview page, you can
  now view their availability via a link to the check availability module.

- A user's account can be activated/deactivated from their userview page.

- The scrolling list of open classes (/onsite/<program>/<instance>/classList)
  now has a landing page where you can toggle settings, such as scroll speed,
  refresh rate, timeblocks, and sorting. WARNING: Don't set the refresh rate
  too low (too little time between refreshes), because this can crash your
  site.

- Volunteers can remove all their shifts and drop out of volunteering for the
  program. It was previously possible to remove some shifts, but a bug
  prevented removing all of them.

- Permissions can be expired/renewed in bulk from the Permission admin panel
  page.

- Fixes to the bulk financial aid approval script.

- Performance improvements to teacherreg.

- Deleting uploaded program files (the manage program documents/materials
  module, not to be confused with the filebrowser for site media files) will
  now ask for confirmation before performing the delete.

- The teacher check-in page now shows more information about a class, including
  its flags.

Updating site installations (developers only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A few new custom ``manage.py`` commands have been defined to make it easier
to update sites (including dev servers):

- ``manage.py update_deps`` - The same as running ``esp/update_deps.sh``.

- ``manage.py install`` - Calls ``app.models.install()`` on all apps that
  have such a function.  Installs any newly-added initial data that wasn't
  already in the database.  In particular, this will install new program
  modules, without the need to open a Django shell and manually call
  ``esp.program.modules.models.install()``.

- ``manage.py recompile_theme`` - Recompiles the installed theme, if there
  is one.  This will redefine the media and template overrides that make up
  the theme, overriding any customizations in the template overrides for
  that theme.  This is the same as opening a Django shell and manually
  calling ThemeController().recompile_theme().  Depending on your
  permissions on the site's ``/tmp`` subdirectory, this command may need to
  be run as the webserver user.

- ``manage.py update`` - The same as running the above three commands, plus
  ``manage.py syncdb`` (to install new tables not under migration controll),
  ``manage.py migrate``, and ``manage.py collectstatic``.

When performing a production site release or pulling many new commits to
your dev server, ``manage.py update`` can be an easy way to get the site
back into a working state.  Running the individual commands can also be
helpful in various situations.

Local unit testing (developers only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running ``manage.py test`` now bypasses running migrations, which saves many
minutes of time.  Between that and the time needed to install dependencies,
it is now much quicker to run the test suite locally than it is to run it on
Travis.  Developers are encouraged to test their changes locally before
pushing to Github, to reduce the need to push subsequent fixes to fix broken
tests.  Developers are also strongly encouraged to write tests for their
changes; locally verifying that new tests are correct is as easy as
``manage.py test app.TestClassName``, which should now run relatively
quickly.

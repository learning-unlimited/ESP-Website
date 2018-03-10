============================================
 ESP Website Stable Release 10 release notes
============================================

.. contents:: :local:

Changelog
=========

New theme: bigpicture
~~~~~~~~~~~~~~~~~~~~~

This release adds a new theme, "bigpicture", based on the custom theme written
by Sean Zhu and used by Splash at Berkeley.  This theme looks a bit more modern
than the existing ones, and should better fit the needs of new chapters.  See
the newly-expanded `themes documentation <../../themes.rst>`_ for how to set up
a new theme.

Here's a screenshot of it live on `Berkeley's site
<https://berkeley.learningu.org>`_:

.. figure:: ../../images/themes/bigpicture.png

   Figure 1: "bigpicture" theme on Berkeley's site

Deletion of login by birthday or school
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before this release, the website included the option for students to log in by
selecting their birthday or school from a list, and then selecting their
username from a list of all student accounts with that birthday or from that
school. This feature has been deleted because it leaks user data: anyone could
go through the list of birthdays or schools one by one and collect this
information for all of our students. Users having trouble logging in are now
encouraged to use the password reset page.

Diff view for template overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(betaveros): #2075

Simplified student reg permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(mgersh): #2133

Lottery frontend program module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(uakfdotb): #1038, #2328

Admin toolbar improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(betaveros): #2234, #2399, #2400, #2452, #2486

Userview improvements
~~~~~~~~~~~~~~~~~~~~~

This release includes a number of improvements to the "user view" page.

- Teachers' names on manage class pages now link to user view.

- The list of classes now has links to the classes' manage and edit pages.

- You can now select a program to use for the quick links.

- The quick links now include a link to the user's accounting page.

- The page now clearly indicates if a user is deactivated.

Volunteer registration improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This release includes a number of improvements to the volunteer registration
functionality.

- TODO(willgearty): #2172

- Volunteer shifts may now be imported from a previous program.

- Volunteer schedules can now be printed.

- The nametag module can now create nametags for volunteers and other user
  groups.

- Volunteer registration statistics are now included in the program dashboard.

"Phase Zero" student lottery system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(willgearty): #2190

Improvements to editable text UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(betaveros): #2247, #2261

- It is now possible to edit a page's title without editing its text.

Teacher Big Board
~~~~~~~~~~~~~~~~~

TODO(willgearty): #2396

Text message & email notification improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(willgearty): #2404, #2410, #2413, #2429, #2497

Minor new features and fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This release includes improvements to the styling of many pages, as well
as some performance improvements.  Other improvements and bug fixes include:

- The deadlines page now correctly shows the status of deadlines that are set
  to open in the future.

- Changing a class's status from "accepted but hidden" to "accepted" from
  the dashboard now works correctly.

- Editing a teacher's availability no longer clears their teacher training or
  interview signups.

- The scrolling class list now only shows class timeblocks.

- Lists of popular classes don't show up on the student reg big board when the
  lottery is not in use.

- The "consistency checks" on individual class manage pages have been removed;
  the scheduling checks module now runs these checks.

- Scheduling checks now have help text explaining what they do.

- You can now add a description when creating a teacher event (interview or
  training).

- It is now possible to hide the FAQ link in the fruitsalad theme.

- Student registration priorities now show up in the correct order.

- Students can now click a button on a class to rank it in phase 2 of the
  lottery.

- The lottery registration pages now show progress bars for the number of
  classes starred.

- The comm panel now has a filter for arbitrary user groups.

- The student reg big board now has line graphs of number of registrations.

- Class cancellation request emails now have a different subject line for each
  class, so they will go to separate threads.

- The onsite class changes grid now supports adding new students to the
  program.

- User morph will no longer fail on students with accents or other special
  characters in their names.

- The user profile options for "graduate student" and "currently enrolled at
  [institution]" have been replaced with a single "specify your affiliation"
  question.

- Applying updates to themes should work more consistently.

- Several bugs in schedule generation are fixed, and the page now gives better
  error text when things go wrong.

- The scheduler now works correctly with classroom names containing commas.

- The class search module now has a "title containing" filter.

- Teacher check-in now has an undo check-in button.

- Fruitsalad pages now have toolbars for editing the navigation bars.

- Grade range help text in the class registration form is now customizable like
  the other fields.

- Added an option to allow teachers to specify a "class style", e.g. lecture
  vs. seminar.  To enable class styles, admins should set the Tag
  ``class_style_choices`` with value in the following JSON format, where the
  first element of each list is the value stored in the database, and the
  second value is the option shown on the form:
  ``[["Lecture", "Lecture Style Class"], ["Seminar", "Seminar Style Class"]]``.

- The K12School admin page no longer crashes.

- Administrators viewing pages which are not accessible to all users will see a
  warning telling them which roles can currently access the page.

- Invalid barcodes no longer cause an error in bulk student check-in.

- The student catalog now allows filtering by grade level rather than showing
  all classes when logged out.

- Room schedules are now sorted alphabetically in the printable.

- Teacher registration now allows setting fixed grade range options, rather
  than allowing any min/max.

- Teachers can now click a button to request that their class be cancelled, if
  they have the ``Teacher/Classes/CancelReq`` permission.  This replaces the
  formerly broken "delete" button.

- The lunch constraint page now clobbers old lunch blocks, allowing lunch
  constraints to be edited.

- The address field in teacher profile may be made optional by setting the
  ``teacher_address_required`` Tag to ``False``.

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
the `themes documentation <../../themes.rst>`_ for how to set up a
new theme.

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

TODO(betaveros)

Simplified student reg permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(mgersh)


Lottery frontend program module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(uakfdotb)

Site now remembers the current program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(betaveros)

Admin toolbar improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(betaveros)

Minor new features and fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Other improvements in this release include:

- Many improvements to styling!

- The deadlines page now correctly shows the status of deadlines that are set
  to open in the future.

- Changing a class's status from "accepted but hidden" to "accepted" from
  the dashboard now works correctly.

- Editing a teacher's availability now won't clear their teacher training or
  interview signups.

- The scrolling class list now only shows class timeblocks.

- It is now possible to edit a page's title without editing its text.

- Lists of popular classes don't show up on the student reg big board when the
  lottery is not in use.

- Some scheduling sanity checks were moved from "consistency checks" on
  individual class manage pages to the dedicated scheduling checks page.

- You can now add a description when creating a teacher event (interview or
  training).

- Volunteer schedules can now be printed.

- It is now possible to hide the FAQ link in the fruitsalad theme.

- Student registration priorities now show up in the correct order.

- Students can now click a button on a class to rank it in phase 2 of the
  lottery.

- Teachers' names on manage class pages now link to userview.

- The viewpay page should now load much faster most of the time.

- The list of classes in userview now has links to the classes' manage and edit
  pages.

- The comm panel now has a filter for arbitrary user groups.

- Inline text editing now has save and cancel buttons instead of "click outside
  the box to save".

- Scheduling checks now have help text explaining what they do.

- The student reg big board now has line graphs of number of registrations.

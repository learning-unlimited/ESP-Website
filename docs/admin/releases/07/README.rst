============================================
 ESP Website Stable Release 07 release notes
============================================

.. contents:: :local:

Changelog
=========

New Django version
~~~~~~~~~~~~~~~~~~

We've updated our code to run on Django 1.8, which is the most recent version. This change should be mostly invisible to non-developers. However, it's a major infrastructure change, so if you see any new issues, please let us know. As always, we recommend testing teacher and student registration before opening them, since your site's configuration might be different from what we're testing on.

Improvements to onsite class changes grid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This release includes several updates to the onsite class changes interface:

- New layout with settings in a collapsible sidebar

- New filter to only show classes that fit in a student's schedule

- Search bar to find a class by title or code

- Fixed a behavior where the browser would temporarily freeze while loading a student's data

- Small updates to wording and styling

Performance improvements
~~~~~~~~~~~~~~~~~~~~~~~~

This release includes several changes which should help improve performance:

- Improved caching on student registration main page

- Documented the fact that setting program cap to 0 will improve performance when no program cap is needed

- Further improvements to the performance of student schedule generation

- Prevented admins from generating all student schedules as PNG, which was causing site downtime


New scheduling checks
~~~~~~~~~~~~~~~~~~~~~

This release adds three new checks to the scheduling checks module:

- "Hosed teachers", which reports teachers who have registered to teach for at least 2/3 of their available hours. Unlike the other checks on this page, it's intended to be run before scheduling, to give you an idea of who might be tricky to schedule, and will not change as you schedule classes.

- "Classes which are scheduled but aren't approved", which checks for unreviewed, rejected, or cancelled classes that are on the schedule.

- "Classes which are the wrong length or have gaps", which checks for classes where the difference between the start time and end time isn't what it's expected to be.

Sentry integration
~~~~~~~~~~~~~~~~~~

This release adds integration with the Sentry exception logging platform (https://getsentry.com/). This change is most useful for developers and system administrators. To copy exceptions to Sentry, configure ``SENTRY_DSN`` with your DSN in ``local_settings.py``. This will not interfere with existing error-reporting mechanisms.

Student schedule extra information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The template that generates student schedules now has a new parameter ``student.last_classes`` available as a template variable. It is a list of classes, one per day from the program, of the student's last class on that day.

By default, this is not shown on the schedule, but it is now possible to write a template override that uses this variable to display the last classes.

Minor feature additions and bugfixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Allowed onsite morphed users to bypass required modules

- Fixed grade options on onsite registration form

- Cleaned up or removed a lot of dead code

- Fixed a display issue in custom forms

- Fixed "any flag" filter in class search

- Added resource requests to class search results page

- Removed all usages of "QSD" and "quasi-static data" and replaced with
  "Editable" and "editable text"

- Improvements to dev setup infrastructure

- Miscellaneous fixes and improvements to various scripts

- Fixed a number of typos

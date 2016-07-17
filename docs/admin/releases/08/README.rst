============================================
 ESP Website Stable Release 08 release notes
============================================

.. contents:: :local:

Changelog
=========

New AJAX scheduler
~~~~~~~~~~~~~~~~~~

TODO(ruthie, herrickc, fbastani, lua, everyone)

Unenroll absent students
~~~~~~~~~~~~~~~~~~~~~~~~

TODO(lua) (and please also add this to program_modules.rst if you haven't already)

Per-grade program caps
~~~~~~~~~~~~~~~~~~~~~~

TODO(benkraft)

Accounting improvements
~~~~~~~~~~~~~~~~~~~~~~~

TODO(btidor), or delete this if it's not user-facing, I forget

Class search improvements
~~~~~~~~~~~~~~~~~~~~~~~~~
With this release, class search allows you to edit your search at the top of the search page.  The results page also includes a new button to email the teachers of a class, a new button to show all classes and all flags which have comments, and an option to randomize the order of search results, along with a minor bugfix.

Onsite print schedules page diagnostic information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(lua)

Onsite class changes grid improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(lua)

User search improvements
~~~~~~~~~~~~~~~~~~~~~~~~
With this release, the User Search box returns users whose cell phone number or
*parent's* email address matches the query, in addition to the matches that were
previously returned. The search is also more robust to case and whitespace issues.

Minor new features and fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Other improvements in this release include:

- The onsite landing page now has a link to the scrolling class list

- Bug in SR07 where form validation errors in teacher profiles could cause a server error is fixed

- Server error when user searching empty string is fixed

- Server error on manage or edit page for nonexistent class is fixed

- Number of students attending program is now available on the studentreg big board

- Student profile module will now correctly show "not a student" error instead of deadline error

- Teachers will only see "class is full" if at least one section is scheduled

- Display improvements to fruitsalad bubblesfront page and editable text attribution line

- Display improvements to alerts on volunteer signup page

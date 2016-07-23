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

The site now supports having per-grade program caps.  The backend for program caps has also been updated, so the logic should be more consistent and correct.

As before, the overall program cap is controlled by setting "Program size max" in the admin panel for the program.  Per-grade caps override this setting, and are controlled by the Tag ``program_size_by_grade``, generally set on a specific program.  The value should be a JSON object; the keys should be strings, either individual grades (as strings, e.g. "7"), or ranges (e.g. "7-9"), and the values should be nonnegative integers.  These ranges should cover all grades for which you want to have a cap.  If you want, they can be overlapping, but that will probably cause worse performance for students in the overlap, since it will have to check both grades.  So it should look something like ``{"7-8": 1000, "9": 300, "10-12" 1500}`` if you want to allow 1000 total 7th and 8th graders, 300 9th graders, and 1500 total 10th-12th graders.

Note: all program caps, and especially per-grade ones, will hurt your site's performance, because we need to check how many students are in the program every time a student tries to join it.  If you don't intend to set a program cap, just leave the field blank, and you'll get much better performance than setting it to a large value.

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

============================================
 ESP Website Stable Release 13 release notes
============================================

.. contents:: :local:

Changelog
=========

User search modules changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- For the Arbitrary User List module, the list of available fields is now filtered based on the selected user type.
- Added a new module to generate a state and/or zipcode map of a set of users.

Student registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (formstack medliab, extra costs, student applications, and lunch selection).
- The extra costs and donation modules now work when a program has no admission cost.

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (teacher availability, teacher training/interviews, and teacher quiz).

Onsite changes
~~~~~~~~~~~~~~
- The search on the teacher check-in page now permits regular expressions and searches all parts of teacher name and class titles/codes.

Theme changes
~~~~~~~~~~~~~

Dashboard changes
~~~~~~~~~~~~~~~~~
- Added stats for the number of scheduled classes, scheduled sections, scheduled class hours, and scheduled class-student hours to the dashboard.
- Changed the Class-Student-Hours Utilization stat on the dashboard to enrolled hours / scheduled hours instead of enrolled hours / approved hours.
- Added attended class-student-hours to the dashboard.
- Added shirt statistics for all teachers with a submitted class, enrolled students, attended students, and volunteers to the dashboard.

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded from Django 1.8.19 to 1.11.29

Minor new features
~~~~~~~~~~~~~~~~~~
- Added options to customize the amount of financial aid granted using the financial aid approval module.
- Added custom widgets to many of the tag settings (preventing potentially site-breaking tag values).

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed an error that occured when trying to access the profile form when morphed as a teacher.

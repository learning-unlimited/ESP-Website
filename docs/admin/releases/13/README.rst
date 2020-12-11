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
- Added new user search filters for students, including number of registered class hours and registered class times.
- Added new user search filters for teachers, including teaching times, training/interview times, and teachers of a particular student.

Student registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (formstack medliab, extra costs, student applications, and lunch selection).
- The extra costs and donation modules now work when a program has no admission cost.

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (teacher availability, teacher training/interviews, and teacher quiz).
- Implemented several improvements to the attendance interface (normal and webapp versions).

Onsite changes
~~~~~~~~~~~~~~
- The search on the teacher check-in page now permits regular expressions and searches all parts of teacher name and class titles/codes.
- Teacher attendance changes also apply to the onsite attendance portal.

Theme changes
~~~~~~~~~~~~~
- Added an account management page at /myesp/accountmanage. All themes now link to this page instead of specific profile/password pages.

Dashboard changes
~~~~~~~~~~~~~~~~~
- Added stats for the number of scheduled classes, scheduled sections, scheduled class hours, and scheduled class-student hours to the dashboard.
- Changed the Class-Student-Hours Utilization stat on the dashboard to enrolled hours / scheduled hours instead of enrolled hours / approved hours.
- Added attended class-student-hours to the dashboard.
- Added shirt statistics for all teachers with a submitted class, enrolled students, attended students, and volunteers to the dashboard.

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded from Django 1.8.19 to 1.11.29
- Upgraded from pillow 3.3.3 to 6.2.2
- Upgraded from psycopg2 2.6.1 to 2.8.6
- Upgraded from numpy 1.7.1 to 1.16.6

Minor new features
~~~~~~~~~~~~~~~~~~
- Added options to customize the amount of financial aid granted using the financial aid approval module.
- Added custom widgets to many of the tag settings (preventing potentially site-breaking tag values).
- Added a public view for emails that have been marked as public (this is a new option in the comm panel). Anonymous (not signed in) users can read a generic (no private information) version of an email at /email/<id> (actual links are on the email monitoring page and comm panel confirmation page).
- The "choice" field for classroom furnishings and floating resources now accepts up to 200 characters.
- Added a default FAQ page at /faq (/faq.html should also work).

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed an error that occured when trying to access the profile form when morphed as a teacher.
- Fixed a bug on the phase zero management page that would prevent the graph from being plotted.
- Fixed a bug that had broken the credit card module.

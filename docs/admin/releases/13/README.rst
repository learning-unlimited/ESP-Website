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
- Added the ability to include and/or multiple user groups when filtering users.

Contact info changes
~~~~~~~~~~~~~~~~~~~~
- Contact infos now require an associated user.
- Old contact infos have been cleaned up, associating student accounts with their emergency contact and guardian contact infos. Any contact infos without associated users have been deleted, since they are useless.
- Users can now be searched by any guardian or emergency contact information (e.g. find a student account by their parent's email address).
- Added a country field to contact infos. If "International" is selected for the state field in a user's profile, the country field is shown.

Student registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (formstack medliab, extra costs, student applications, and lunch selection).
- The extra costs and donation modules now work when a program has no admission cost.

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (teacher availability, teacher training/interviews, and teacher quiz).
- Implemented several improvements to the attendance interface (normal and webapp versions).

Class management changes
~~~~~~~~~~~~~~~~~~~~~~~~
- All of the section cancellation forms have been merged into a single form allowing admins to cancel multiple sections at once for the same reason.

Volunteer registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Help text is now shown for the comments field.
- Required fields are now marked with asterisks.

Onsite changes
~~~~~~~~~~~~~~
- The search on the teacher check-in page now permits regular expressions and searches all parts of teacher name and class titles/codes.
- Teacher attendance changes also apply to the onsite attendance portal.
- Added teacher lists to classes on the grid-based class changes interface. Also added teachers as a filterable field.
- Fixed the "Hide past timeblocks" option in the grid-based class changes interface.
- Added an attendance-through-time chart on the attendance landing page that shows the cumulative number of students that have checked in to the program and the number of students that are attending classes for each hour.

Theme changes
~~~~~~~~~~~~~
- Added an account management page at /myesp/accountmanage. All themes now link to this page instead of specific profile/password pages.

Dashboard changes
~~~~~~~~~~~~~~~~~
- Added stats for the number of scheduled classes, scheduled sections, scheduled class hours, and scheduled class-student hours to the dashboard.
- Changed the Class-Student-Hours Utilization stat on the dashboard to enrolled hours / scheduled hours instead of enrolled hours / approved hours.
- Added attended class-student-hours to the dashboard.
- Added shirt statistics for all teachers with a submitted class, enrolled students, attended students, and volunteers to the dashboard.

Minor new features
~~~~~~~~~~~~~~~~~~
- Added options to customize the amount of financial aid granted using the financial aid approval module.
- Added custom widgets to many of the tag settings (preventing potentially site-breaking tag values).
- Added a public view for emails that have been marked as public (this is a new option in the comm panel). Anonymous (not signed in) users can read a generic (no private information) version of an email at /email/<id> (actual links are on the email monitoring page and comm panel confirmation page).
- The "choice" field for classroom furnishings and floating resources now accepts up to 200 characters.
- Added a default FAQ page at /faq (/faq.html should also work).
- Timeslots for classrooms and floating resources on the resources page are no longer grouped if they occur <15 minutes apart.
- Added a new tag `grade_increment_date` that allows admins to adjust when student grades increment (e.g. before or after a summer program).
- Added a button to the scheduling checks page that, when clicked, causes all of the checks to refresh at some interval that is specified by the user.

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed an error that occured when trying to access the profile form when morphed as a teacher.
- Fixed a bug on the phase zero management page that would prevent the graph from being plotted.
- Fixed a bug that had broken the credit card module.
- Fixed a bug where students that had yet to fill out a profile would cause the phase zero management page to break. If such students are in the phase zero lottery, they are now reported on the management page.
- Fixed a bug that reported an error when a class's duration was some whole number of hours.
- Fixed the alignment of the headers in the scheduling app when rooms have really long names.
- Fixed the wrong class length scheduling check.
- Fixed the "lottery preferences" count on the student big board (was previously including enrollments).
- Fixed the completion certificate to now include the program email and name.
- Fixed elements that were supposed to be full width (e.g. surveys).
- Fixed the cutoff at the bottom of the manage programs page.
- Fixed pluralizations and capitalizations in the admin pages.

Development changes
===================

Development server changes
~~~~~~~~~~~~~~~~~~~~~~~~~~
- The development server VM has been upgraded to Ubuntu 20.04 (from Ubuntu 14.04). LU web developers will need to upgrade their local development servers by following the instructions in `vagrant.rst <https://github.com/learning-unlimited/ESP-Website/blob/main/docs/dev/vagrant.rst#upgrading-your-personal-dev-vm>`_.

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded Django (1.8.19 -> 1.11.29)
- Upgraded pillow (3.3.3 -> 6.2.2)
- Upgraded psycopg2 (2.6.1 -> 2.8.6)
- Upgraded numpy (1.7.1 -> 1.16.6)
- Upgraded sorttable.js (2 -> 2e3)
- Upgraded node.js (0.10.x -> 14.x LTS)
- Upgraded less (1.3.1 -> 1.7.5)
- Upgraded bootstrap (2.0.2 -> 2.3.2)

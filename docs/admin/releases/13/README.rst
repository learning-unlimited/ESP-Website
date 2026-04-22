============================================
 ESP Website Stable Release 13 release notes
============================================

.. contents:: :local:

Changelog
=========

Moderator integration
~~~~~~~~~~~~~~~~~~~~~
Moderators (or observers, teaching assistants, etc) for individual sections are now fully integrated and supported by the entirety (or close to it) of the website. This integration includes several additions and improvements to the website, which are activated by (and only by) enabling the new TeacherModeratorModule:

- A form is added to teacher registration which allows users to indicate if they are interested in moderating. They can specify how many time blocks they want to moderate, select which categories they are most interested in, and provide any comments they might have.
- The ajax scheduling page has a new panel that enables the assignment of moderators to specific sections. Various filters are included to filter moderators, and there is also an option to only show sections which match the preferred categories of the selected moderator. In this functionality, teacher availability is used as moderator availability. Also, while moderators specify how many time blocks they would like to moderate, there is no actual enforcement of this (but the interface does show when it has been exceeded).
- Moderator info is listed on the /manageclass, /coteachers (admin version only), /editavailability, and /classavailability pages.
- Assigned moderators have their section assignments listed on the main teacher registration page (beneath taught classes), where they can see details about the sections and access the attendance page.
- Similar information is on the teacher webapp (in the schedule and in the specific section info pages).
- Moderators are listed on and can be checked-in via the onsite teacher check-in page.
- Moderators are listed in the onsite attendance module for classes without attendance.
- Several new printables are available which have moderator info (e.g. individual schedules, moderator schedule spreadsheet).
- Several existing printables have moderator information (e.g. class list, room schedules).
- Moderator stats are shown on the dashboard and teacher big board.

Custom forms
~~~~~~~~~~~~
Overhauled the custom forms creation frontend page and backend functionality. Most notably, this now allows for custom forms to be edited (even after users have responded to a custom form). This includes adding, removing, and editing fields, instructions, and pages/sections. To edit a custom form, you can select it from within the creation frontend or with one of the new links on the custom form landing page. In addition, the following changes/fixes were made:

- Fixed the handling of long field titles in the responses table.
- Added an "Other" option to the gender field.
- Fixed a bug/error that occurred when users entered responses that were too long for a text field.
- The custom form landing page now lists the ID of each custom form (for admin reference).
- Custom forms can now be linked to specific program registration modules (e.g., the teacher custom form module), and the appropriate tags will be created upon form creation.
- HTML in field labels and help texts is now rendered for users.
- Better error handling and reporting during custom form creation.
- The field type of existing fields can now be changed.
- Fixed a bug where blank options were added to multi-answer fields (e.g., checkboxes, dropdown).
- Fixed the teacherinfo and contactinfo fields.
- Field help text is now shown in the form preview as it will be shown in the real form. Correct answers are also indicated on the form preview.

Program management changes
~~~~~~~~~~~~~~~~~~~~~~~~~~
- When importing the settings from a previous program, class registration module info settings, student class registration module info settings, and tag settings are now copied to the new program. New programs based on previous programs should now function almost exactly like the previous programs.
- Added new program tags to change the tolerance (in minutes) of contiguous blocks for the teacher availability page and for scheduling purposes.
- Added custom widgets to many of the tag settings (preventing potentially site-breaking tag values).
- Added a new tag `grade_increment_date` that allows admins to adjust when student grades increment (e.g., before or after a summer program).
- Added a frontend user interface to add, remove, edit, and import line items.
- Fixed text wrapping for the module questions on the new program and program settings pages.
- Fixed some modules that were unintentionally being included by default (class change request module).
- Added module questions for the Class Change Request, Moderator, and Student Acknowledgment modules.
- Fixed a bug that occurred when no modules were selected.
- Fixed a bug that caused an invalid calculation of the program admission cost.
- The "choice" field for classroom furnishings and floating resources now accepts up to 200 characters.
- Timeslots for classrooms and floating resources on the resources page are no longer grouped if they occur <15 minutes apart.
- Added documentation for modules, which is shown on the main program management page. The additional modules on this page are now alphabetized.
- Fixed section alignment on the main program management page.

User search modules changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- For the Arbitrary User List module, the list of available fields is now filtered based on the selected user type.
- Added a new module to generate a state and/or zipcode map of a set of users.
- Added new user search filters for students, including number of registered class hours and registered class times.
- Added new user search filters for teachers, including teaching times, training/interview times, and teachers of a particular student.
- Added the ability to include and/or exclude multiple user groups when filtering users.
- All user search filters are now cleared whenever you change user type or switch between the different tabs.

Contact info changes
~~~~~~~~~~~~~~~~~~~~
- Contact infos now require an associated user.
- Old contact infos have been cleaned up, associating student accounts with their emergency contact and guardian contact infos. Any contact infos without associated users have been deleted, since they are useless.
- Users can now be searched by any guardian or emergency contact information (e.g., find a student account by their parent's email address).
- Added a country field to contact infos. If "International" is selected for the state field in a user's profile, the country field is shown.

Student registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (formstack medliab, extra costs, student applications, and lunch selection).
- The extra costs and donation modules now work when a program has no admission cost.
- Added an option to the student lottery management page to not open student registration once the lottery has been run.
- Added enrollment limit options (max timeslots and max sections) to the class lottery.
- Fixed a bug affecting ranks beyond the first choice in the class lottery.

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Some modules will no longer show up in registration if they are not set up correctly (teacher availability, teacher training/interviews, and teacher quiz).
- Implemented several improvements to the attendance interface (normal and webapp versions).
- The default availability for the teacher availability form is now none (instead of all/full).
- Added links on the class edit page to the coteachers and catalog preview pages.

Volunteer registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Help text is now shown for the comments field.
- Required fields are now marked with asterisks.

Class management changes
~~~~~~~~~~~~~~~~~~~~~~~~
- All of the section cancellation forms have been merged into a single form allowing admins to cancel multiple sections at once for the same reason. Each section has it's time and date listed.

Statistics and data visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- New queries have been added to the /manage/statistics page, including multiprogram statistics on student and teacher registration. The results of these queries include graphs to visualize the change of various metrics across programs through time (e.g. # class-student-hours approved).
- Adjusted the text of the link on the "Manage All Programs" page to reflect the addition of non-student statistics.

Scheduling changes
~~~~~~~~~~~~~~~~~~
- Added a button to the scheduling checks page that, when clicked, causes all of the checks to refresh at some interval that is specified by the user.
- Fixed the alignment of the headers in the ajax scheduler when rooms have really long names.
- Fixed the wrong class length scheduling check.
- Fixed the "Mismatched rooms and meeting times" and "Classes not completely scheduled or with gaps" scheduling checks for classes with assigned floating resources.
- Fixed the "Teachers with limited availability" scheduling check for cases where teachers somehow had no availability.
- Fixed the highlighting on the ajax scheduler for when a user is trying to schedule a single-block class on a day with a single lunch block.
- Added scheduling checks to the ajax scheduler that let you see if there are any errors or inconsistencies with how classes have been scheduled (e.g., capacity mismatches, resource mismatches, availability mismatches, double-booked teachers). This does not include all checks from the scheduling checks module, and we plan to keep the scheduling checks module around for the foreseeable future.
- The class directory on the ajax scheduler can now be sorted by ID, category, length, capacity, and teacher availability.
- Fixed a bug that caused sections with floating resources to not be shown in the class directory on the ajax scheduler.
- Fixed a bug where pressing enter in the class search box would refresh the page.

Onsite changes
~~~~~~~~~~~~~~
- The search on the teacher check-in page now permits regular expressions and searches all parts of teacher names and class titles/codes.
- Teacher attendance changes also apply to the onsite attendance portal.
- Added teacher lists to classes on the grid-based class changes interface. Also added teachers as a filterable field.
- Fixed the "Hide past timeblocks" option in the grid-based class changes interface.
- Added an attendance-through-time chart on the attendance landing page that shows the cumulative number of students that have checked in to the program and the number of students that are attending classes for each hour.
- Fixed a page-breaking bug on the teacher check-in page (this was also patched on SR12).
- Added sorting options to the grid-based class changes page (length of section, class ID, fullness, and category).
- Added barcode scanning to teacher check-in. Admins can use physical scanners or personal smart devices.
- The main /onsite page has been redesigned to look like the main /manage page.

Theme changes
~~~~~~~~~~~~~
- Added an account management page at /myesp/accountmanage. All themes now link to this page instead of specific profile/password pages.
- Fixed a bug with the admin bar styling on the fruitsalad theme.
- Centered the main content for the bigpicture theme.
- Fixed the color of some buttons for the fruitsalad theme when using the default theme settings.
- Fixed the background color of the top tabs on the fruitsalad theme.
- Fixed a range of bugs related to arbitrary table widths in the bigpicture theme.
- Added a default FAQ page at /faq (/faq.html should also work).

Dashboard changes
~~~~~~~~~~~~~~~~~
- Added stats for the number of scheduled classes, scheduled sections, scheduled class hours, and scheduled class-student hours to the dashboard.
- Changed the Class-Student-Hours Utilization stat on the dashboard to enrolled hours / scheduled hours instead of enrolled hours / approved hours.
- Added attended class-student-hours to the dashboard.
- Added shirt statistics for all teachers with a submitted class, enrolled students, attended students, and volunteers to the dashboard.
- Updated the caching of all of the statistics on the dashboard, so they should now always be up-to-date.

Survey changes
~~~~~~~~~~~~~~
- Survey results are now cached, which should result in much faster load times when viewing any survey result page.

Printable changes
~~~~~~~~~~~~~~~~~
- Changed individual teacher schedules (accessed from the userview page) to only show scheduled classes.
- Fixed the top margin of the catalog sorted by category printable.
- Fixed the completion certificate to now include the program email and name.
- Added barcodes to teacher schedules and made teacher schedules prettier.
- Fixed the combo selector on the nametags page.

Minor new features
~~~~~~~~~~~~~~~~~~
- Added options to customize the amount of financial aid granted using the financial aid approval module.
- Added a public view for emails that have been marked as public (this is a new option in the comm panel). Anonymous (not signed in) users can read a generic (no private information) version of an email at /email/<id> (actual links are on the email monitoring page and comm panel confirmation page).
- Added links to usernames in the scheduler, financial aid approval module, and the manage events page.
- Added a student search box to the accounting module.
- Pages that use the usersearch form interface now list the module name.

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed an error that occured when trying to access the profile form when morphed as a teacher.
- Fixed a bug on the phase zero management page that would prevent the graph from being plotted.
- Fixed a bug that had broken the credit card module.
- Fixed a bug where students that had yet to fill out a profile would cause the phase zero management page to break. If such students are in the phase zero lottery, they are now reported on the management page.
- Fixed a bug that reported an error when a class's duration was some whole number of hours.
- Fixed the "lottery preferences" count on the student big board (was previously including enrollments).
- Fixed elements that were supposed to be full width (e.g., surveys).
- Fixed the cutoff at the bottom of the manage programs page.
- Fixed pluralizations and capitalizations in the admin pages.
- Fixed an issue that had broken email "plain" redirects.
- Fixed some error pages so that theme and admin toolbar content is rendered properly.
- The subject of a comm panel email is now required, which prevents errors caused by sending comm panel emails without subjects.
- Fixed a bug on the phase zero management page when the grade cap tag was not set.
- Fixed logging errors when sending emails.
- Fixed errors that occurred when emailing users with particular symbols in their names.
- Fixed a bug where selecting a timeslot on a different day on the onsite attendance module would have unexpected behavior.
- Fixed email links on the stripe failure page.

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
- Upgraded jQuery (1.7.2 -> 1.12.4)
- Upgraded jQuery UI (1.8.9 -> 1.12.1)
- Upgraded jqGrid (4.3.1 -> 5.5.2)
- Upgraded django-debug-toolbar (1.5 -> 1.11.1)

August 2021 Patch
=================

Custom forms
~~~~~~~~~~~~
- Several bug fixes and enhancements to the custom form builder
- Added the correct answer option to more custom form field types
- Fixed the rendering of custom forms with multiple pages
- The teacher and student custom form modules now have separate handlers; they no longer show up in registration if custom forms are not setup and assigned via tags
- There are now separate records for filling out student and teacher custom forms, allowing for separate searching for users

Minor new features
~~~~~~~~~~~~~~~~~~
- Duplicate program names are now prevented
- Added moderator tshirt stats to the dashboard
- A class's status is now updated in the dashboard interface when it is changed via the popup
- Added a module that lets you add or remove users from a new or existing user group
- The teacher_profile_hide_fields, student_profile_hide_fields, volunteer_profile_hide_fields, educator_profile_hide_fields, guardian_profile_hide_fields, and teacherreg_hide_fields tags now show the possible valid options in the tag settings interface
- Added many more filter options to /classsearch (e.g., duration, grade, capacity, number of sections, and optional request fields)
- The /manage/emails page is now cached
- Modified the styling of inline student schedules (webapp and student reg mainpage) to clarify when classes are multiple blocks long
- Userview links now specify the program of interest so the sidebar links are more relevant
- Course materials are now always shown in the catalog, even when a class is full
- Naturally sort classrooms when importing them
- Prevent importing of some tags when copying an old program
- When adding a coteacher, check that they are available for the scheduled times of the class (if the class is scheduled)
- Redesigned the theme palette management
- The theme font size and family pickers now show previews of the sizes and families
- Added "Return to main program management page" links to (almost) all management module pages
- Added a new module that lets admins deactivate arbitrary sets of users (use caution, this is not easy to undo)
- Redesigned the deadline management page
- Added a scheduling check for moderators moderating classes with categories they didn't select
- Added class popularity graphs to the student big board (replacing the old popularity lists)
- Removed the TextMessageModule (the module that adds a text box at the bottom of the student registration page for a phone number) because it is no longer needed (we ask for phone numbers and permission to text students in the student profile)
- Added enrollment and attendance plots to the students hours query on /manage/statistics
- Added a confirmation page when importing volunteer shifts from a previous program

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed the scheduler popup for open classes
- Escape program name in LaTeX templates
- Fixed attributes when custom form field types are changed
- Restored the "multiple classes with the same resource" scheduling check
- Floating resources no longer have duplicate times if there are multiple instances
- Fixed (hopefully for the last time) the associated asterisks and styling of required fields in forms
- Fixed the /manage/mergeaccounts page and added a link to it from /manage/programs
- Fixed the ajax scheduler to support timeslots of any length
- Fixed the display of the selected grade range when editing a class as a teacher
- Fixed the fruitsalad theme so the tabs in the left nav bar can now have multiple lines of text
- Fixed the message panel in the ajax scheduler so it always shows when there is a class or moderator scheduling error
- Fixed the behavior of sortable tables when they had complex layouts or only a single row of data
- Fixed cancelled classes being included on the teacher availability form and when deciding whether a coteacher could be added to a class
- Fixed browser console errors complaining about non-unique ids on the resources management page

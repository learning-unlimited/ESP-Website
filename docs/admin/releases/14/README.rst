============================================
 ESP Website Stable Release 14 release notes
============================================

.. contents:: :local:

Changelog
=========

User search modules
~~~~~~~~~~~~~~~~~~~
- The default minimum and maximum grade filters are now set to the minimum and maximum grades of the program (to prevent erroneous emails to very old students)
- There is now a list of commonly used searches to simplify the user selection process
- Printables that use the user search controller now have default settings
- Improved the performance of searching for users (hotfixed to Stable Release 13)
- Added options to search by students/teachers that have enrolled in/attended/taught for previous programs
- Fixed some combination lists
- Fixed the combination lists to prevent "NOT"-only selections.

Program records
~~~~~~~~~~~~~~~
- Records can now be bulk set for an arbitrary user list with the new User Records Module
- A set of records can be set as required for student or teacher registration using tags ("student_reg_records" and "teacher_reg_records")
- These records are shown on the student/teacher registration mainpage, the userview page, the student checklist printable, and the teacher list printable

AJAX Scheduler
~~~~~~~~~~~~~~
- Shortcuts are now documented
- Switched the default availability setting for moderators
- Classes can now be sorted by teacher "hosedness"
- If a server error is encountered while saving a scheduling comment, the comment is now reverted
- Added a button to print the scheduling matrix

Accounting
~~~~~~~~~~
- Line items can now be marked as covered by financial aid (or not, e.g., t-shirts). When financial aid is granted, it will only be granted in an amount that covers only the line items that are marked as covered by financial aid.
- Added a new page to see all of the accounting for a user across all programs (/accounting/user)

Student and teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Teachers no longer show up as their own coteachers on the teacher registration mainpage
- When students are unenrolled from classes, their lottery preferences are no longer expired
- Fixed bugs related to the registration progress bar interface
- Fixed a bug where a teacher's availability could include times for which they signed up for training, etc (this may fix instances where teachers were able to register more hours of classes than they should have been able to)
- Fixed the order of modules on the student and teacher registration mainpages (sorting order is now required -> seq -> isCompleted)
- Added a warning banner to the top of all required modules (this banner and the deadline banner are also now included in all themes)
- Fixed the bottom of the phase zero confirmation page being cut off
- Added a module that allows students to get a completion certificate after attending a program (see the "student certificate" tag for options)
- The maps in the student and teacher webapps are now entirely free (but do require a Google Cloud API key which is set as a tag)
- Walking directions in the student and teacher webapps are now fulfilled entirely by Google Maps (will open the app on mobile devices)

Optional and required extra costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- The Extra Costs Module now shows all required or optional extra costs that are not related to admission or financial aid
- If there are any required items, the module is required during registration, and the form will require selections to be made for those required items before it can be submitted
- Required items may have associated costs and/or options; this is now the supported method for asking students which kind of lunch/meal they would like (e.g., pizza vs. sandwich)
- The numbers of students that have requested particular options can be seen on the program dashboard
- The sibling discount form has also been added to this module (if enabled in the program settings) and the discount value now reflects the respective program setting
- The Splash Info Module, which previously included the lunch options and sibling discount forms, has been completely removed

Program management changes
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added an admin checkbox interface for the steps that are required for ensuring a program is completely setup
- Rounded the hours stats on the dashboard
- Added the default values to the help text in the tag settings UI
- Fixed the performance of /manage/emails for sites that sent emails to lots of recipients (this was previously so bad that it could cause the entire server to crash)
- Added an undo button to the student lottery management page
- Split teacher registration tags into "Teacher Registration Settings", "Moderator Settings", and "Class Registration Settings"
- Admins can now set custom landing pages for students and teachers with the "student_home_page" and "teacher_home_page" tags, respectively
- Added buttons to the custom form response interface to bulk download files
- Classes are now colored by category in the popularity graphs on the student big board
- Tweaked the tooltip of the popularity graphs on the student big board
- Student and teacher registration status is now shown on the userview page
- Fixed the color of messages on the deadline management page
- Added statistics to the dashboard for "teachers who have submitted a class and have not taught for a program" and "students who are enrolled and have not enrolled in the past"

Onsite changes
~~~~~~~~~~~~~~
- Added an option to the grid-based class changes interface to check-in (or not check-in) students when changing their schedules
- Fixed a bug that prevented the "full" status of classes from updating on the grid-based class changes page

Printables changes
~~~~~~~~~~~~~~~~~~
- The student schedules pdf is now downloaded as a file instead of opening in the browser
- Clarified the description of the teacher/moderator check-in lists

Theme changes
~~~~~~~~~~~~~
- Changed the default font families for the default theme customizations ("Default" and "Rupaa")
- Fixed many bugs in the theme editor, including when loading and saving customizations

Minor new features
~~~~~~~~~~~~~~~~~~
- Fixed the styling of the survey responses pdf
- Fixed the list of programs that are shown after updating your profile (filtered by grade for students, now shown for volunteers)
- Various error and success messages are now shown as banners to increase visibility
- Added an anonymous option to the contact form
- Added a filter for expired vs unexpired permissions and student registrations in the admin panel
- Users without a profile are now prompted to fill one out upon logging in
- Forms can no longer be submitted more than once before the new page loads, hopefully preventing some rare database errors and duplicate program charges

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed the link in the admin deadline banner for several pages
- Fixed the email address for some users on the userview page
- Fixed the login redirect behavior when a user is already logged in
- LaTeX in class titles is no longer rendered on the survey results page to prevent errors
- Fixed a bug that duplicated (or triplicated) help text in one of the buttons for the QSD editor
- Fixed a bug that previously allowed non-admins to access 'manage' QSD pages
- Fixed text wrapping in the webapp
- Fixed the caching of the catalog and dashboard when scheduling classes and running the class lottery
- Fixed teacher userview links on the dashboard
- Fixed errors that occured when attempting to send emails with weird characters
- Fixed the completion certificate printable for when a user's name had weird characters

Development changes
===================

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded jQuery (1.12.4 -> 3.6.0)
- Upgraded jQuery UI (1.12.1 -> 1.13.0)

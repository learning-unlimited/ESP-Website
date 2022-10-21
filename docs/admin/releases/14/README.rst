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
- Fixed multiselect filters (cherry-picked to SR-13)

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
- Added the ability to swap sections in the scheduler
- Fixed a bug that prevented sections from being rescheduled to an overlapping time (e.g., from 10-12 to 9-11)
- Added dates to the timeslots (column headers) in the scheduler
- Added class style to the scheduler
- Added a class category scheduling check to the scheduler (colors classes by category)
- The capacity mismatch scheduling check now distinguishes between a class being too small (shades of blue) for the room versus too big for the room (shades of red)

Accounting
~~~~~~~~~~
- Line items can now be marked as covered by financial aid (or not, e.g., t-shirts). When financial aid is granted, it will only be granted in an amount that covers only the line items that are marked as covered by financial aid.
- Added a new page to see all of the accounting for a user across all programs (/accounting/user)
- All "Paid for a program" records have been converted to transfers; these records are now deprecated

General registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fixed bugs related to the registration progress bar interface
- Fixed the order of modules on the student and teacher registration mainpages (sorting order is now required -> seq -> isCompleted)
- Added a warning banner to the top of all required modules (this banner and the deadline banner are also now included in all themes)
- The maps in the student and teacher webapps are now entirely free (but do require a Google Cloud API key which is set as a tag)
- Walking directions in the student and teacher webapps are now fulfilled entirely by Google Maps (will open the app on mobile devices)
- Fixed some links to program and class documents

Student registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- When students are unenrolled from classes, their lottery preferences are no longer expired
- Added a module that allows students to get a completion certificate after attending a program (see the "student certificate" tag for options)
- Fixed the bottom of the phase zero confirmation page being cut off

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Teachers no longer show up as their own coteachers on the teacher registration mainpage
- Fixed a bug where a teacher's availability could include times for which they signed up for training, etc (this may fix instances where teachers were able to register more hours of classes than they should have been able to)
- Consolidated the many buttons on the teacher class registration mainpage into two dropdown menus
- Uploaded documents can now be renamed

Optional and required extra costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- The Extra Costs Module now shows all required or optional extra costs that are not related to admission or financial aid
- If there are any required items, the module is required during registration, and the form will require selections to be made for those required items before it can be submitted
- Required items may have associated costs and/or options; this is now the supported method for asking students which kind of lunch/meal they would like (e.g., pizza vs. sandwich)
- The numbers of students that have requested particular options can be seen on the program dashboard
- The sibling discount form has also been added to this module (if enabled in the program settings) and the discount value now reflects the respective program setting
- The Splash Info Module, which previously included the lunch options and sibling discount forms, has been completely removed
- The name that students record for the sibling discount can be retrieved as a field in the arbitrary user list

Program management changes
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added an admin checkbox interface for the steps that are required for ensuring a program is completely set up
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
- Added the ability to edit existing teacher events (e.g., trainings, interviews) on the teacher event page
- Fixed running the phase zero lottery with complex grade caps (e.g., a single capacity across multiple grades)
- Added error messages to the phase zero lottery page if the grade cap tag is not set properly
- Fixed the role name of lottery winners (removed the "s")
- Clarified the help text for the "Priority limit" setting and removed the "Use priority" setting in the student registration settings
- Uploaded documents can now be renamed
- Made several fixes and enhancements to the lunch constraints form (e.g., fixed the initial values of the form, lunches are no longer deleted if the form is resubmitted)

Class and section status management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- "Rejection" can now only happen before a class is scheduled, whereas "cancellation" can now only happen after a class is scheduled (this change is now implemented on the class management page,  dashboard, and class search page)
- When a section's status is changed, if all sections of a class now have the same status, the status of the class is changed to that status
- Section management forms now are submitted individually
- Sections and classes can now only be cancelled via the cancellation form
- Sections can no longer be approved unless their parent class is also approved

Death of the admin pages
~~~~~~~~~~~~~~~~~~~~~~~~
- Added a user interface for adding and editing class categories and class flag types (/manage/categoriesandflags)
- Added a user interface to approve and reject grade change requests on the userview page
- Added a user interface to create, edit, and delete permissions for individual users (on what was previously the Deadline Management page)
- Added a user interface to create, edit, and delete URL and email redirects (/manage/redirects)
- Added a user interface to edit registration receipts on the program settings page
- Added a user interface to change the sequence and requiredness of program modules
- Added a user interface for adding and removing students to/from the student lottery
- The link to the admin pages has been removed for all themes

Onsite changes
~~~~~~~~~~~~~~
- Added an option to the grid-based class changes interface to check-in (or not check-in) students when changing their schedules
- Fixed a bug that prevented the "full" status of classes from updating on the grid-based class changes page

Printables changes
~~~~~~~~~~~~~~~~~~
- The student schedules pdf is now downloaded as a file instead of opening in the browser
- Clarified the description of the teacher/moderator check-in lists
- Clarified the nametag option help text

Theme changes
~~~~~~~~~~~~~
- Changed the default font families for the default theme customizations ("Default" and "Rupaa")
- Fixed many bugs in the theme editor, including when loading and saving customizations
- The icon dropdown for the bigpicture theme settings now shows the actual icons

Minor new features
~~~~~~~~~~~~~~~~~~
- Fixed the styling of the survey responses pdf
- Fixed the list of programs that are shown after updating your profile (filtered by grade for students, now shown for volunteers)
- Various error and success messages are now shown as banners to increase visibility
- Added an anonymous option to the contact form
- Added a filter for expired vs unexpired permissions and student registrations in the admin panel
- Users without a profile are now prompted to fill one out upon logging in
- Forms can no longer be submitted more than once before the new page loads, hopefully preventing some rare database errors and duplicate program charges
- Added a link to edit a teacher's biography on the account manage page (if the user is a teacher)
- The custom form landing page now has custom forms sorted by the programs or courses with which they are associated

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
- Fixed a small number of forms that could not be submitted via javascript
- Fixed the wording on the profile form for new users
- Fixed the review_single survey links for admin survey review pages
- Fixed the behavior of registration receipts and the registration cancellation button
- Fixed a bug where mailman details were included during account registration even when mailman was not enabled
- Fixed the help text for the K12 school field for student profiles
- The class search in the admin toolbar now only appears if the program has the class search module enabled
- Fixed statistics for number of approved classes and teachers when approved classes have no approved sections

Development changes
===================

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded jQuery (1.12.4 -> 3.6.0)
- Upgraded jQuery UI (1.12.1 -> 1.13.0)

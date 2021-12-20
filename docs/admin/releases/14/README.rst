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

Minor new features
~~~~~~~~~~~~~~~~~~
- Classes are now colored by category in the popularity graphs on the student big board
- Tweaked the tooltip of the popularity graphs on the student big board
- Changed the default font families for the default theme customizations ("Default" and "Rupaa")
- Fixed the styling of the survey responses pdf
- Added an undo button to the student lottery management page
- Rounded the hours stats on the dashboard
- Split teacher registration tags into "Teacher Registration Settings", "Moderator Settings", and "Class Registration Settings"
- Added a warning banner to the top of all required modules (this banner and the deadline banner are also now included in all themes)
- Student and teacher registration status is now shown on the userview page
- Fixed the list of programs that are shown after updating your profile (filtered by grade for students, now shown for volunteers)
- Admins can now set custom landing pages for students and teachers with the "student_home_page" and "teacher_home_page" tags, respectively
- Teachers no longer show up as their own coteachers on the teacher registration mainpage
- The student schedules pdf is now downloaded as a file instead of opening in the browser
- Various error and success messages are now shown as banners to increase visibility
- Added an anonymous option to the contact form
- Added an admin checkbox interface for the steps that are required for ensuring a program is completely setup
- Added a filter for expired vs unexpired permissions and student registrations in the admin panel

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed many bugs in the theme editor, including when loading and saving customizations
- Fixed a bug where a teacher's availability could include times for which they signed up for training, etc (this may fix instances where teachers were able to register more hours of classes than they should have been able to)
- Fixed the performance of /manage/emails for sites that sent emails to lots of recipients (this was previously so bad that it could cause the entire server to crash)
- Fixed the bottom of the phase zero confirmation page being cut off
- Fixed the link in the admin deadline banner for several pages
- Fixed the email address for some users on the userview page
- Fixed the color of messages on the deadline management page
- Fixed bugs related to the registration progress bar interface
- Fixed the order of modules on the student and teacher registration mainpages
- Fixed the login redirect behavior when a user is already logged in
- LaTeX in class titles is no longer rendered on the survey results page to prevent errors

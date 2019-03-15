============================================
 ESP Website Stable Release 11 release notes
============================================

.. contents:: :local:

Changelog
=========

Resource improvements
~~~~~~~~~~~~~~~~~~~~~
- Added ability to modify resource choices from the resources management module.
- Added ability to specify if a resource type should be hidden during teacher registration.
- Added ability to specify resource type choices as furnishings for classrooms.
- Added ability to specify if only one option may be selected for a resource request during teacher registration.
- Added ability to import resource types, floating resources, and classrooms (with their furnishings) from a 
  previous program. All of the above properties are preserved when importing. Admins may also select a subset of
  the old resources to be imported to the new program.

Automatic Scheduling Assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TODO(jerrywu64): #2442

Userview improvements
~~~~~~~~~~~~~~~~~~~~~
- Added a link on the userview page to a user's volunteer schedule (if they are volunteering).
- Added a link on the userview page to unenroll a student from all of their classes for the selected program.
- Fixed two-column layout of the userview page.

Class search improvements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Added buttons to approve, unreview, or reject all of the classes shown on the class search page.
- Added ability to filter class search queries by resource requests (e.g. Classroom), including filtering by specific resource type choices (e.g. Lecture Hall).
- Added links to make printables of the classes shown on the class search page.

Onsite improvements
~~~~~~~~~~~~~~~~~~~
- For chapters that use barcodes for student checkin, the barcodes can now be scanned 
  in using your device's camera, so a physical barcode scanner is no longer needed. The
  default behavior is to checkin the student automatically upon each successful scan. The 
  page produces a beep for each new barcode that is scanned.
- Fixed the layout of the teacher checkin page so as not to intefere with the admin toolbar in some themes.
- Fixed the keyboard functionality of the teacher checkin page so shorcuts now function as described.
- Added a button on the teacher checkin page that allows admins to text all teachers that are
  not yet checked in yet (if the chapter has Twilio configured).
- Added buttons on the teacher checkin page that allows admins to easily move to the next or previous time slots.
- Added links to all onsite pages that return admins to the main onsite page.
- Fixed the Onsite "New Student Registration" page.
- Fixed the Onsite "Advanced Checkin" page.

QSD and comm panel improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TODO(willgearty): #2592, #2666, #2692

rich text and source code editor

Email improvements
~~~~~~~~~~~~~~~~~~
TODO(benjaminkraft): #2549, #2604, #2627, #2667

- Message requests in the admin panel now list their creation time/date and whether or not they have been processed.

Theme fixes
~~~~~~~~~~~
- In fruitsalad theme, the login button text now is the same font as everything else.
- In fruitsalad theme, the contact info in the top left will no longer disappear when on the login form page.
- In fruitsalad theme, now show links and search fields for all "current" programs in the admin bar.
- In circles theme, the user search box is now the correct width.

Minor new features and fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a default login help page /myesp/loginhelp.html that admins can modify.
- Arbitrary user lists now allow admins to get guardian name, email, and cell phone.
- The credit card success page for Stripe now has a line about what the charge will appear on the statment as.
- Fixed ordering of two-phase lottery priorities, now supports custom display names.
- Fixed the classrosters admin printable. Teachers should use the /section_students and /class_students pages to access their class rosters.
- Volunteer requests are now separated by date, and admin pages now show dates of volunteer requests and offers.
- Updated admin coteacher page to be more user-friendly. Now shows all teachers, including admins, and admins can now remove themselves from classes.
- Added a coteacher deadline, allowing the coteachers page to be closed independently of the teacher registration main page.
- Added dates to the classes on the teacher bio page.
- Added option to override users' texting preferences in the group texting module. This is 
  primarily designed for texting volunteers or teachers, since they can't set their texting preferences.
  However, this can also be used to text all students, regardless of their texting preferences.
- Fixed the sorting of the categories at the top of the catalog to match the order of the categories in the catalog.
  If the catalog is not sorted by category, category headings are no longer displayed (see tag 'catalog_sort_fields').
  The /fillslot page is now sorted just like the catalog.
- Added a lunch deadline for students. The "Student Lunch Selection" module depends on this deadline.
- Teacher schedules now include "Accepted but Hidden" classes.
- Fixed an error where texting would fail (without finishing) if an invalid phone number was encountered.
- Added duration field on the manage class page, which can be modified if no sections of the class have been scheduled yet.
- Teacher registration grade ranges can now be program specific (see tag 'grade_ranges').
- Fixed walk-in registration and class import errors introduced by teacher registration grade ranges.
- Fixed an error that occurred when students had no amount due.
- Fixed errors that occurred when timeslot durations resulted in floating point numbers with more than two decimal places.
- Fixed handling of the 'finaid_form_fields' tag.
- Profile form now populates DOB and graduation year even if the form errors.
- Custom form responses can now be viewed even if users are accidentally deleted.
- Teacher big board no longer breaks if a class accidentally has no sections.
- Teacher big board calculations now consistently exclude lunch classes.
- Fields should no longer be autocompleted by browsers in the comm panel, group text module, or arbitrary user list (specifically the 'username' field).
- Chapters can now upload .ico files in the filebrowser without changing their file extension before and after upload.
- Added a printable that lists all of the classes for each teacher (sorted by teacher last name). Classes with multiple teachers are listed for each teacher.
- The new availability layout for teachers has been extended to volunteer and admin modules. Admins can now check and edit availability on the same page.

Known Issues
============
- The catalog may have blank spaces within or between class descriptions.
- Not all required fields in the profile form are marked as required.
- Importing classrooms before importing the resource types they use will cause resource types to be created with no choices.
- The catalog can not be sorted using the start time of sections.
- The nametag printables include deactivated users, causing them to include include differeent sets of users from other printables.

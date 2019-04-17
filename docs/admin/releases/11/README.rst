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
This is a new module intended for use in parallel with the AJAX scheduler to find good scheduling choices for
individual sections. When this module is enabled, a new link will appear for each section in the scheduler
with the text "Optimize". This will bring the user to a new interface to find an appropriate time and
classroom for the section. Documentation is provided on this page detailing how admins can configure the
module before scheduling to better suit their program's needs, mostly through the use of custom tags.

Userview improvements
~~~~~~~~~~~~~~~~~~~~~
- Added a link on the userview page to a user's volunteer schedule (if they are volunteering).
- Added a link on the userview page to unenroll a student from all of their classes for the selected program.
- Added a link on the userview page to a teacher's biography.
- Fixed two-column layout of the userview page.
- User types are now listed on the userview page.
- Classes on the userview page now link to their catalog (in addition to the preexisting links to the manage and edit pages).
- Sections on the userview page are now colored based on section status (instead of using the class status).

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
- Fixed the layout of the teacher checkin page so as to not intefere with the admin toolbar in some themes.
- Fixed the keyboard functionality of the teacher checkin page so shortcuts now function as described.
- Added a button on the teacher checkin page that allows admins to text all teachers that are
  not yet checked in yet (if the chapter has Twilio configured).
- Added buttons on the teacher checkin page that allows admins to easily move to the next or previous time slots.
- Teachers without contact info no longer break the teacher checkin page.
- Added links to all onsite pages that return admins to the main onsite page.
- Fixed the Onsite "New Student Registration" page.
- Fixed the Onsite "Advanced Checkin" page.

Editable text and comm panel improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added ability to include dates in teacher and volunteer schedules within comm panel emails.
- Fixed the layout of the combination list page in the comm panel (and other user select modules).
- Added a rich text editor to the comm panel that includes most functions that are common in
  Microsoft Word/Google Docs, including stylings (bold, strikethrough, underline, and italics),
  indenting, lists, fonts, headings, colors, alignment, tables, and symbols.  The editor supports 
  the pasting of rich text from various sources (including Microsoft Word), and images can be included
  from external sources or the filebrowser via URL (direct upload may be supported in a future release).
  The template tags are now located in a dropdown menu with the ``{{}}`` label. Admins can click the
  ``</>`` button to use a source code editor and write HTML code as before.
- All comm panel emails are now HTML, so ``<html>`` tags are no longer necessary. We will address
  the spam filter implications of this in a future release.
- Fixed a bug in the generation of schedules in comm panel emails
- Added a rich text editor to editable text fields (QSD) like the comm panel (see above).
- **If you are using the source code editor in the comm panel or editable text fields, it is advised
  that you switch back to the rich text editor view before saving/proceeding.**
  
Printables improvements
~~~~~~~~~~~~~~~~~~~~~~~
- Fixed the classrosters admin printable. Teachers should use the ``/section_students`` and ``/class_students`` pages to access their class rosters.
- Added a printable that lists all of the classes for each teacher (sorted by teacher last name). Classes with multiple teachers are listed for each teacher.
- Fixed some printables that broke when non-approved classes were specified manually. Added more options for Classes by Time/ID/Title/Teacher printables.
- Added a printable that shows class popularity (enrollment and lottery metrics).
- Teacher schedules now include "Accepted but Hidden" classes.

Email backend improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Implemented optimizations for really large email requests.
- Added more logging to the email backend for better debugging of future email problems.
- Updated the default bounces email address to address one of the most common reasons emails from the comm panel were being marked as spam.
- Message requests in the admin panel now list their creation time/date and whether or not they have been processed ('processed' means that all of the email texts have been set up and the server is now sending the emails).

Theme fixes
~~~~~~~~~~~
- In fruitsalad theme, the login button text now is the same font as everything else.
- In fruitsalad theme, the contact info in the top left will no longer disappear when on the login form page.
- In fruitsalad theme, now show links and search fields for all "current" programs in the admin bar.
- In circles theme, the user search box is now the correct width.
- In bigpicture theme, fixed a signin/signout loop on the signout page.

Minor new features and fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a default login help page ``/myesp/loginhelp.html`` that admins can modify.
- Arbitrary user lists now allow admins to get guardian name, email, and cell phone.
- The credit card success page for Stripe now has a line about what the charge will appear on the statment as.
- Fixed ordering of two-phase lottery priorities, now supports custom display names.
- Volunteer requests are now separated by date, and admin pages now show dates of volunteer requests and offers.
- Updated admin coteacher page to be more user-friendly. Now shows all teachers, including admins, and admins can now remove themselves from classes.
- Added a coteacher deadline, allowing the coteachers page to be closed independently of the teacher registration main page.
- Added more explicit steps for adding a coteacher to the coteacher page.
- Added dates to the classes on the teacher bio page.
- Added option to override users' texting preferences in the group texting module. This is 
  primarily designed for texting volunteers or teachers, since they can't set their texting preferences.
  However, this can also be used to text all students, regardless of their texting preferences.
- Fixed the sorting of the categories at the top of the catalog to match the order of the categories in the catalog.
  If the catalog is not sorted by category, category headings are no longer displayed (see tag ``catalog_sort_fields``).
  The ``/fillslot`` page is now sorted just like the catalog.
- Added a lunch deadline for students. The "Student Lunch Selection" module depends on this deadline.
- Fixed an error where texting would fail (without finishing) if an invalid phone number was encountered.
- Added duration field on the manage class page, which can be modified if no sections of the class have been scheduled yet. The duration field was also added to the class search page.
- Added class style (if used) and resource requests to the manage class and class search pages.
- Teacher registration grade ranges can now be program specific (see tag ``grade_ranges``).
- Fixed walk-in registration and class import errors introduced by teacher registration grade ranges.
- Fixed an error that occurred when students had no amount due.
- Fixed errors that occurred when timeslot durations resulted in floating point numbers with more than two decimal places (e.g. 50 minutes). This should fix errors that were encountered during scheduling, on class manage pages, and when adding coteachers, among others.
- Fixed handling of the ``finaid_form_fields`` tag.
- Profile form now populates DOB and graduation year even if the form errors.
- Custom form responses can now be viewed even if users are accidentally deleted.
- Teacher big board no longer breaks if a class accidentally has no sections.
- Teacher big board calculations now consistently exclude lunch classes.
- Teacher big board now shows data on registered and approved classes.
- Big boards now display graphs even if there is no data to show.
- Hours statistics on the dashboard are now show for registered and approved classes.
- Fields should no longer be autocompleted by browsers in the comm panel, group text module, or arbitrary user list (specifically the 'username' field).
- Chapters can now upload .ico files in the filebrowser without changing their file extension before and after upload.
- The new availability layout for teachers has been extended to volunteer and admin modules. Admins can now check and edit availability on the same page.
- When using a template program to create a new problem, module info from the template program will now be copied to the new program (including ``seq`` values, whether or not they are ``required``, and the ``required_label``)
- Made login errors clearer
- Added teacher interview and training descriptions to the manage page for these events.
- Fixed the format of the inline student schedule (on the student reg mainpage).

Known Issues
============
- The catalog may have blank spaces within or between class descriptions.
- Not all required fields in the profile form are marked as required.
- Importing classrooms before importing the resource types they use will cause resource types to be created with no choices.
- Importing classrooms without complete availability results in them only being available for the first timeslot.
- The catalog can not be sorted using the start time of sections.
- The nametag printables include deactivated users, causing them to include differeent sets of users from other printables.
- The ajax scheduler sometimes does not differentiate between classes with different background colors.
- The new QSD rich text editor breaks pre-existing HTML anchors (links to parts of the current page). These can be replaced with javascript as described `here <https://github.com/learning-unlimited/ESP-Website/issues/2701>`_.
- Some themes do not display the big boards as intended.

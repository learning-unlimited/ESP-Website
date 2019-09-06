============================================
 ESP Website Stable Release 11 release notes
============================================

.. contents:: :local:

Changelog
=========

Automatic scheduling assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is a new module intended for use in parallel with the AJAX scheduler to find good scheduling choices for
individual sections. When this module is enabled, a new link will appear for each section in the scheduler
with the text "Optimize". This will bring the user to a new interface to find an appropriate time and
classroom for the section. Documentation is provided on this page detailing how admins can configure the
module before scheduling to better suit their program's needs, mostly through the use of custom tags.

Financial aid approval module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A new program module that allows admins to easily view and approve financial aid applications in bulk.

Resource improvements
~~~~~~~~~~~~~~~~~~~~~
- Added ability to modify resource choices from the resources management module.
- Added ability to specify if a resource type should be hidden during teacher registration.
- Added ability to specify resource type choices as furnishings for classrooms.
- Added ability to specify if only one option may be selected for a resource request during teacher registration.
- Added ability to import resource types, floating resources, and classrooms (with their furnishings) from a 
  previous program. All of the above properties are preserved when importing. Admins may also select a subset of
  the old resources to be imported to the new program.

Userview improvements
~~~~~~~~~~~~~~~~~~~~~
- Added a link on the userview page to a user's volunteer schedule (if they are volunteering).
- Added a link on the userview page to unenroll a student from all of their classes for the selected program.
- Added a link on the userview page to a teacher's biography.
- Fixed two-column layout of the userview page.
- User types are now listed on the userview page.
- Classes on the userview page now link to their catalog (in addition to the preexisting links to the manage and edit pages).
- Sections on the userview page are now colored based on section status (instead of using the class status).
- Reorganized userview sidelinks into three categories (Administrative, Student, and Teacher).
- Moved teacher information above student information on userview page, so student information is now next to parent and guardian contact information.
- Changed conditions for showing different information sections on the userview page. Made it more explicit when contact info is missing.

Class search improvements
~~~~~~~~~~~~~~~~~~~~~~~~~
- Added buttons to approve, unreview, or reject all of the classes shown on the class search page.
- Added ability to filter class search queries by resource requests (e.g. Classroom Type), including filtering by specific resource type choices (e.g. Lecture Hall).
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
- Fixed a bug in the generation of schedules in comm panel emails.
- Added a rich text editor to editable text fields (QSD) like the comm panel (see above).
- **If you are using the source code editor in the comm panel or editable text fields, it is advised
  that you switch back to the rich text editor view before saving/proceeding.**
- Updated instructions for making QSD (editable text) pages.
  
Printables improvements
~~~~~~~~~~~~~~~~~~~~~~~
- Fixed the classrosters admin printable. Teachers should use the ``/section_students`` and ``/class_students`` pages to access their class rosters.
- Added a printable that lists all of the classes for each teacher (sorted by teacher last name). Classes with multiple teachers are listed for each teacher.
- Fixed some printables that broke when non-approved classes were specified manually. Added more options for Classes by Time/ID/Title/Teacher printables.
- Added a printable that shows class popularity (enrollment and lottery metrics).
- Teacher schedules now include "Accepted but Hidden" classes.
- Added alternative ``.csv`` versions for some class, section, and teacher printables.

Email backend improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Implemented optimizations for really large email requests.
- Added more logging to the email backend for better debugging of future email problems.
- Updated the default bounces email address to address one of the most common reasons emails from the comm panel were being marked as spam.
- Message requests in the admin panel now list their creation time/date and whether or not they have been processed ('processed' means that all of the email texts have been set up and the server is now sending the emails).
- Added ability to use Sendgrid as the email backend.

Theme fixes
~~~~~~~~~~~
- In fruitsalad theme, the login button text now is the same font as everything else.
- In fruitsalad theme, the contact info in the top left will no longer disappear when on the login form page.
- In fruitsalad theme, now show links and search fields for all "current" programs in the admin bar.
- In circles theme, the user search box is now the correct width.
- In circles theme, replaced the login button and fixed navbar styling.
- In bigpicture theme, fixed a signin/signout loop on the signout page.

Big board fixes
~~~~~~~~~~~~~~~
- Fixed styling of big board numbers to override some theme styling and to prevent overlap of numbers.
- Teacher big board no longer breaks if a class accidentally has no sections.
- Teacher big board calculations now consistently exclude lunch classes.
- Teacher big board now shows data on registered and approved classes.
- Big boards now display graphs even if there is no data to show.

Arbitrary user list improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Arbitrary user lists now allow admins to get guardian name, email, and cell phone for student users.
- When the selected users are teachers, selecting the "school" or "grad year" fields will fill in their university affiliation (if entered) and graduation year. Student users will still have these fields as before as well.
- Arbitrary user lists no longer refer to "contacts" to avoid confusion with communications panel.

Coteacher improvements
~~~~~~~~~~~~~~~~~~~~~~
- Updated admin coteacher page to be more user-friendly. Now shows all teachers, including admins, and admins can now remove themselves from classes.
- Added a coteacher deadline, allowing the coteachers page to be closed independently of the teacher registration main page.
- Added more explicit steps for adding a coteacher to the coteacher page.

Availability page improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- The new availability layout for teachers has been extended to volunteer and admin modules. Admins can now check and edit availability on the same page.
- The teacher availability page now identifies (with a red border) which scheduled sections conflict with the teacher's availability (and allows for teachers to mark themselves, or admins to mark teachers, as available for timeslots when they are teaching but weren't previously available).
- The new availability layout is now co-opted for a new Class Availability page which shows when a class can be scheduled (like in the scheduler) and which teachers of the class are causing unavailability at particular times due to being unavailable or teaching another class. If a section of the class is scheduled at a time when any teachers are unavailable, those timeslots are identified with a red border (and the hover text specifies which teachers have conflicts). You can get to this page from the scheduler, the manage class page, or the class search page.

Language improvements
~~~~~~~~~~~~~~~~~~~~~
- Changed mentions of "ESP" to program name.
- Removed hyphens from sufficiently old/common words, such as "email."
- Removed stray periods and other punctuation.
- Fixed several misspellings, phrasing, etc.
- Fixed formatting of some hyperlinks.
- Changed "Pre-registration" to "registration" (we specify "onsite reg" elsewhere, so online reg should be the default).
- Changed the infamous "Fitted for women" to "Fitted cut" and "plain" to "Straight cut."
- Updated a few defaults for courtesy/professionalism (editable text can be changed if anyone prefers the old way).
- Made "parents should not be here" warnings more noticeable.
- Made form errors (the "This field is required" message) bold and red to increase visibility.
- Updated the program creation form language so it doesn't make it sound so scary, and made its formatting nicer.
- Removed Q tree references.
- Removed old SAT score variables.
- Made Stripe failure page more salient (different from success page), made other minor fixes to Stripe message & formatting.
- The credit card success page for Stripe now has a line about what the charge will appear on the statment as.
- Added a few more general email addresses.
- Made login errors clearer.
- Added teacher interview and training descriptions to the manage page for these events.

Minor new features
~~~~~~~~~~~~~~~~~~
- Added a default login help page ``/myesp/loginhelp.html`` that admins can modify. (Other pages linked to this page, but it did not exist by default.)
- Fixed ordering of two-phase lottery priorities, now supports custom display names.
- Volunteer requests are now separated by date, and admin pages now show dates of volunteer requests and offers.
- Added dates to the classes on the teacher bio page.
- Added option to override users' texting preferences in the group texting module. This is 
  primarily designed for texting volunteers or teachers, since they can't set their texting preferences.
  However, this can also be used to text all students, regardless of their texting preferences.
- Added a lunch deadline for students. The "Student Lunch Selection" module depends on this deadline.
- Added duration field on the manage class page, which can be modified if no sections of the class have been scheduled yet. The duration field was also added to the class search page.
- Added class style (if used) and resource requests to the manage class and class search pages.
- Teacher registration grade ranges can now be program specific (see tag ``grade_ranges``).
- Profile form now populates DOB and graduation year even if the form errors.
- Profile form now shows teacher fields instead of student fields if a user has both user types (under the assumption that they used to be a student and now they are a teacher).
- Hours statistics on the dashboard are now shown for registered and approved classes.
- Fields should no longer be autocompleted by browsers in the comm panel, group text module, or arbitrary user list (specifically the 'username' field).
- Chapters can now upload .ico files in the filebrowser without changing their file extension before and after upload.
- Added LU logo as default favicon.
- When using a template program to create a new problem, module info from the template program will now be copied to the new program (including ``seq`` values, whether or not they are ``required``, and the ``required_label``).
- Added links to some useful pages to the QSD box in /manage/programs. These pages were not previously linked to by any other current page on the site: Custom forms page, ``/manage/pages/``, ``myesp/makeadmin/``, ``/statistics/`` and ``/manage/flushcache``. In addition, there are now instructions on how to create a new page, links to various website guides, and a reminder to contact mentors, websupport, or Chapter Services with additional troubles or requests.

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed the sorting of the categories at the top of the catalog to match the order of the categories in the catalog.
  If the catalog is not sorted by category, category headings are no longer displayed (see tag ``catalog_sort_fields``).
  The ``/fillslot`` page is now sorted just like the catalog.
- Fixed styling of classes in the catalog when there was an error message (e.g. student is outside of the grade range).
- Fixed an error where texting would fail (without finishing) if an invalid phone number was encountered.
- Fixed a bug that marked the profile form module as complete for teacher registration if it was completed for student registration (or vice versa).
- Fixed walk-in registration and class import errors introduced by teacher registration grade ranges.
- Fixed an error that occurred when students had no amount due.
- Fixed errors that occurred when timeslot durations resulted in floating point numbers with more than two decimal places (e.g. 50 minutes). This should fix errors that were encountered during scheduling, on class manage pages, and when adding coteachers, among others.
- Fixed handling of the ``finaid_form_fields`` tag.
- Restyled ``list.html`` so static pages' URLs don't run into next column.
- Fixed the format of the inline student schedule (on the student reg mainpage).
- Fixed the coloration of sections in the AJAX scheduler.
- Custom form responses can now be viewed even if users are accidentally deleted.

Minor bug fixes released in August 2019
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fixed alignment of the gender field in the profile form.
- Rounded popularity printable percent capacity to 2 decimals.
- Added a link to the conflicting teacher's availability page on the coteachers page.
- Fixed the rounding of class durations on the class search and class manage pages (previously class lengths were often listed as 1 minute shorter than the truth).
- Fixed the logic of the error message on the teacher availability page (previously this used the admin's availability instead of the teacher's availability).
- Within-page anchors on QSD pages (e.g. on FAQ pages) work as intended again.
- The teacher big board now works for all programs. If the classes for a program are not timestamped (pre-2016), the graph will be omitted.
- Fixed the gaps that showed up in the catalog when using the grade filter.
- Limited time blocks shown on the resources page to Class Time Blocks and Open Class Time Blocks (i.e. teacher training and interview blocks will no longer be displayed here).
- Fixed the height of the comm panel dropdown menus to avoid extending beyond the bottom of the page.
- Dropdowns to select programs for importing things are now filtered to only programs that have things to import and are not the current program (e.g. resources, volunteer requests).
- Classrooms can now be imported with matched/incomplete availability again (i.e. not selecting the "Complete availability" option).
- Added help text for the "Global?" option in the resource types management form. This option is now hidden unless the ``allow_global_restypes`` tag is set to ``True``.
- Teacher addresses are now optional by default in the profile form. Addresses can be required for teachers by setting the ``teacher_address_required`` Tag to ``True``.
- The class search bar in the fruitsalad admin bar is now hidden if the class search module is not enabled.
- Teacher availability links on the userview, class availability, and admin coteachers pages are now hidden if the check availability module is not enabled.
- In the case where a user has no registration profiles associated with programs, the program dropdown on the userview page now displays a null option (previously, this misleadingly showed a program as selected even though it wasn't).
- Fixed the logic for the conflict error message on the class availability page.
- When coteachers are added to a class by an admin or teacher (e.g. admin setting availability manually, then adding on the teach or manage coteachers page), their registration profile is now updated appropriately (i.e. the correct program is now selected on their userview page).
- Fixed the handling of program registration profiles. If a user's most recent profile is fairly recent (last five days), they won't need to fill out a new one for a new program. This is most relevant for concurrent programs, but also makes it easier on new users who want to register for a program immmediately after making an account.
- Added styling to indicate on the userview page whether a teacher has set their availability yet.
- Fixed profile handling for the userview page so information on the userview page correctly reflects the profile of the selected program.
- Emails are no longer archived in an LU email address (but comm panel emails are still archived on sites and other emails still get copied to the director email address).
- The catalog now only says "check out the other sections!" if there is actually at least one other approved and scheduled section.
- The tag ``volunteer_help_text_comments`` can be used to override the help text of the comments field in the volunteer form (which must be enabled by setting the ``volunteer_allow_comments`` tag to ``True``).
- Volunteers that register without an account are now sent a password recovery email upon submitting the volunteer form (because an account is created for them but they are not told the password).
- Only scheduled and approved classes (including approved but hidden classes) now appear in a teacher's schedule.
- The volunteer csv now includes the comments field.
- Saving a QSD that someone else has edited since you started editing will now result in an error message.
- The survey dump now includes the survey number in the sheet title.
- 0th grade no longer shows up in the profile form.
- The tag ``admin_home_page`` can be used to specify the relative or absolute page that admins should be redirected to upon signing in.

Known issues of new features
============================
- The new QSD rich text editor can break in some weird edge cases. See the discussion `here <https://github.com/learning-unlimited/ESP-Website/issues/2746>`_.
- Users may notice errors reported in the browser console related to jquery.initialize. These errors do not affect the performance or functionality of the pages.

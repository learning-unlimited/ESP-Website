============================================
 ESP Website Stable Release 12 release notes
============================================

.. contents:: :local:

Changelog
=========

Attendance
~~~~~~~~~~
We've implemented a set of tools for teachers and admins to manage student class attendance:

1. We've added a new page ``/teach/[one]/[two]/section_attendance`` that allows teachers to take attendance for a particular section (including unenrolled students). Teachers can either use a checkbox interface or scan barcodes (with their phones) like at student check-in to mark students as attending the class. Options are provided to allow teachers to enroll students in their class if they were not previously enrolled. The page is linked to from the main teacher registration page (for sections that are approved and scheduled). The page also has a dropdown menu for the teacher to select one of their sections for attendance. Attendance records for a class expire at midnight of the day they were set (this is useful for recurring classes, such that teachers can mark separate attendance for each instance of the same section).
2. We've added an onsite module that summarizes attendance statistics/details. The page has a similar dropdown to select a particular timeslot for attendance. The page is linked to from the main onsite page (provided the module is enabled). The module will assume that you are interested in attendance records for the present day, but you can use the date picker to see a summary of attendance for a previous day (in the case of recurring classes). This page also has links to email, text, or get information for users that are checked in, playing hooky, or attending the wrong class.
3. We've added an onsite module that allows you to check\ **out** individual students (in the case where a student is leaving for lunch, etc.) or all students (in the case where the day has finished and you want to record checkin again for the next day). The module also allows admins to unenroll students from the classes that will be missed when they are checked out from the program. Checked out records will be reflected on the website in a number of ways:

   - The onsite checkin page now lists when a student was checked in and checked out. Checkins or checkouts can now be undone on this page. Students can also be checked out from this page by unchecking the "Attending" box.
   - Checked out students are accounted for in the onsite attendance module (#2 above).
   - The barcode checkin page will not raise an error if a student is checked out (and will then check them back in).
   - Attendance numbers in the grid-based class canges and grid-based status pages are now based on attending students that are not checked out.
   - There is a new "Currently checked out students" option for the comm panel, arbitrary user list, and group text panel.
   - The teacher attendance page (#1 above) will only mark a student as checked in if they are not checked out.

Onsite Webapps
~~~~~~~~~~~~~~
We've added mobile-friendly interfaces for teachers and students for tools that are commonly used at Splash events.

1. The teacher interface, available at ``/teach/[one]/[two]/teacheronsite`` (if enabled), has a live schedule, Google maps of campus (with directions to classrooms if set up), section details (including email addresses), section rosters (with attendance functionality), and a page for the Splash teacher survey and student survey responses. If no surveys are setup, this navigation panel is hidden (the new survey creation page can be used to set these up).
2. The student interface, available at ``/learn/[one]/[two]/studentonsite`` (if enabled), has a live schedule (with class changes), Google maps of campus (with directions to classrooms if set up), a course catalog, and an interface to fill out the student survey. If no survey is setup, this navigation panel is hidden (the new survey creation page can be used to set these up).

Student Acknowledgement
~~~~~~~~~~~~~~~~~~~~~~~
Similar to the teacher acknowledgement module, this module will force students to agree to some conditions (ie a code of conduct) during student registration.

Generic program links
~~~~~~~~~~~~~~~~~~~~~
We've added the ability to use generic links that redirect to the most recent/current program (the one that is latest in time). The links are of the form ``[site].learningu.org/[tl]/[one]/current/[view]``, where ``[site]`` is the specific chapter site; ``[tl]`` is "teach", "learn", "manage", "volunteer", or "onsite"; ``[one]`` is the program type (e.g. "Splash", "Sprout", "HSSP"); and ``[view]`` is the specific page/view (e.g. "teacherreg", "studentreg", "dashboard", etc). Further arguments can be included after the view if they are normally included for that view.

Program Creation and Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a page where you can modify all of the settings for a program (``/manage/[one]/[two]/settings``), including settings associated with the program itself, teacher registration, and student registration.
- Added a page where you can modify the tag settings for a program (``/manage/[one]/[two]/tags``), with documentation and defaults for every tag.
- Added a page where you can modify the global tag settings (``/manage/tags``), with documentation and defaults for every tag.

Onsite changes
~~~~~~~~~~~~~~
- You can now customize the teacher check-in text message in a template override (``program/modules/teachercheckinmodule/teachertext.txt``)
- When texting all unchecked-in teachers through the teacher check-in page, you can now opt to skip teachers of classes with at least one checked-in teacher.
- The main onsite page will now only show links to modules that are enabled.
- The grid-based class changes page has been remodeled to better display the lengths of classes within the grid.
- Fixed a bug where the time range displayed for a multi-hour class on the grid-based class changes page would be incorrect.

Floating Resources changes
~~~~~~~~~~~~~~~~~~~~~~~~~~
- Admins can now specify how many of a particular floating resource are available (e.g. 5 VGA adapters or 10 expo markers)
- When assigning a floating resource on the /manageclass page, a user-friendly error is now displayed if the selected floating resource is not available for the specified timeslots

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Links to class and teacher email addresses are now included for each class on a teacher's main registration page.

Printables changes
~~~~~~~~~~~~~~~~~~
- Revamped student schedules. They are now in a portrait layout and include amount due, names of teachers for classes, and barcodes for check-in.
- The ``studentchecklist`` printable now updates the statuses in the checklist based on the records through the website of whether students have been checked-in, have paid, or have turned in forms.
- Admins can now use an arbitrary list of users (like that used in the comm panel or schedule generator) to generate nametags.
- Nametags now have the option to have barcodes on the backs (or really anything, with template overrides).
- Reorganized the printables page and condensed the "Class and Section Lists" section by implementing dropdown menus.
- The "All Classes Spreadsheet" now has a form that allows admins to choose which fields to include in the CSV download.

Scheduler changes
~~~~~~~~~~~~~~~~~
- Room requests are now included in the scheduler.
- You can now filter classrooms (rows) in the scheduler by room capacity, resource, and name.
- You can now filter classes in the scheduler by resource requests and flags.
- You can now filter classes in the scheduler to only those taught by admins.
- Added an option in the "Class Filters" tab to override teacher availability when scheduling classes. This will NOT override lunch constraints, already scheduled classes, or whether a class will actually fit time-wise where you are trying to schedule it.
- The scheduler now works even if the Teacher Availability Module is not enabled (teachers will have full availability).

Flag and classsearch changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Flags are now in a separate category on the dashboard (and are prettier).
- Newly created flags no longer disappear when you click on their header.
- Clickable items (such as flags and class titles) are now more obvious and neater on the classsearch page and other places flags are shown.
- Flag names are now shown on the teacher checkin page without having to expand the class. Clicking on the flag names reveals the flag details.
- Added a class flag printable.

Survey changes
~~~~~~~~~~~~~~
- Added a user interface for admins to build surveys for students and teachers to fill out after a program is over. Built-in question types include "Yes-No Response", "Multiple Choice", "Checkboxes", "Short Answer", "Long Answer", "Numeric Rating", and "Labeled Numeric Rating". Survey questions can be viewed in their rendered layout to see how they'll ultimately look in the survey. Once surveys have been created, they can be imported for future programs.
- Built-in surveys are now shown in the student and teacher onsite webapp interfaces. Additionally, teachers can see survey responses for their classes in the teacher onsite webapp interface.
- Admins can now specify which students and teachers have access to the built-in program surveys with the tags "survey_teacher_filter" and "survey_student_filter". These tags will also be used to calculate the number of potential participants when displaying survey results.
- All survey questions are now bolded (previously some question types were not).
- Survey result histograms for countable questions now show the entire possible range of answers.
- The ``top_classes`` page for program surveys works again.
- Fixed survey dumps in cases where survey names had certain forbidden characters.

Theme changes
~~~~~~~~~~~~~
- Links on the barebones and bigpictures themes that previously said "Admin Home", now correctly say "Administration Pages" like other themes
- Fixed the fruit salad header for instances where the program name was very long and overlapped with the login information. Also changed styling associated with the login box to make things symmetrical (and removed the text "Hello,").
- Fixed the colors of the buttons presented when editing a QSD/editable text on the bigpicture theme. Button colors will also now properly change when updated in the bigpicture theme settings.
- Fixed the width of the class edit form and the teacher preview table in the bigpicture theme.

Minor new features
~~~~~~~~~~~~~~~~~~
- You can now include unreviewed classes in the scheduling diagnostics.
- You can now sort the results of a user search. The results also now include the last program for which a user has a profile (has registered).
- The teacher major and affiliation fields are now included as options in the arbitrary user list module.
- Phase zero is no longer included in the student registration checkboxes interface. More details are now included on the lottery confirmation page.
- The teacher availability search bar now only searches teachers (for the autocomplete). The rapid check-in and formstack medical/liability student search bars now only search students (for the autocomplete).
- Added a new page where admins can check the status of comm panel emails (``/manage/emails/``).
- Moved the grade change request link in the profile form to just under the grade field.
- Profile form now is more specific about whose contact info is being collected. Student phone numbers can be left blank if the tag "require_student_phonenum" is set to "False."
- Added "View on site" links to a number of user-related pages in the administration pages.
- Added duration-from-now labels next to deadline form fields.
- Made the text on the profile form clearer when users can not change their grade/dob.
- Added emailcodes to the subjects of all emails to class/section lists (i.e. "[prefix] [emailcode] Subject"). The prefix can be changed in the admin pages (and will be omited from the subject if not set).
- Changed the theme of the administration pages. Each section on the main page is now moveable, collapsible, and closable.
- The student lottery can now support lottery groups of any size (specified by the "student_lottery_group_max" tag). If the tag is set to 1, options to join groups will not be shown to students.

Minor bug fixes
~~~~~~~~~~~~~~~
- The debug toolbar remains active (if specified by the admin) when morphing into users.
- All required fields are now marked as such in the profile form.
- Cancellation emails now permit symbols, such as apostrophes.
- The background for the userview page will always be at least as long as the content on the page.
- You can now actually sort the classes on the dashboard by many fields.
- Fixed a bug that allowed teachers to see the rosters for any sections/classes, even if they weren't teachers for them.
- Fixed some bugs in the class catalog related to hiding classes and registration buttons. Unscheduled sections are now considered "Full".
- Fixed a bug where sections weren't completely unscheduled when their classrooms were deleted.
- Fixed a bug where admins would need to flush the cache after changing the lunch constraints to make them update in the scheduler.
- Fixed many instances where a student's grade was listed as the current grade but should have been the grade at the time of the program.
- The grade change request link is no longer displayed in the profile form for new users or users that can change their grade in the form.
- Unscheduled sections and classes with no sections are no longer shown in the two-phase student lottery registration.
- The "allow_change_grade_level" tag is now treated as a boolean tag.
- Removed deprecated onsite status page.
- Fixed multiple bugs associated with the "teacher_profile_hide_fields" tag.
- Fixed the handling of the "num_stars" tag.
- Fixed cases where the list of a teacher's classes would include rejected classes even when specified to not include rejected classes.
- Removed the "Classrooms have been imported" message on the resources page which would appear when any kind of resource was imported.
- Removed the "Catalog" deadline because it didn't do anything.
- Fixed erroneous cases where "(not required)" should have been listed next to modules in student and teacher registration but wasn't.

Known issues of new features
============================

============================================
 ESP Website Stable Release 12 release notes
============================================

.. contents:: :local:

Changelog
=========

Privacy Policy
~~~~~~~~~~~~~~
The LU Board has approved a new `Privacy Policy <https://www.learningu.org/about/privacy/>`_, which governs how you collect and use the data on your site. These terms have been posted on your sites and must be followed.

Attendance
~~~~~~~~~~
We've implemented a set of tools for teachers and admins to manage student class attendance:

1. We've added a new page ``/teach/[one]/[two]/section_attendance`` that allows teachers to take attendance for a particular section (including unenrolled students). Teachers can either use a checkbox interface or scan barcodes (with their phones) like at student check-in to mark students as attending the class. Options are provided to allow teachers to enroll students in their class if they were not previously enrolled. The page is linked to from the main teacher registration page and from the webapp interface (for sections that are approved and scheduled). The page also has a dropdown menu for the teacher to select one of their sections for attendance. Attendance records for a class expire at midnight of the day they were set (this is useful for recurring classes, such that teachers can mark separate attendance for each instance of the same section). Splash at Yale made a `brief video tutorial <https://youtu.be/KV7i1G8s63k>`_ for this page.
2. We've added an onsite module that summarizes attendance statistics/details. The page has a similar dropdown to select a particular timeslot for attendance. The page is linked to from the main onsite page (provided the module is enabled). The module will assume that you are interested in attendance records for the present day, but you can use the date picker to see a summary of attendance for a previous day (in the case of recurring classes). This page also has links to email, text, or get information for users that are checked in, playing hooky, or attending the wrong class.
3. The onsite grid-based class changes will also show the number of students marked as attending a class (meaning there are now four numbers: "class attendance/program attendance/enrollment/capacity" for each class).
4. The onsite attendance module also has an interface for onsite users to take attendance for any classes like how teachers can (see #1 above).
5. We've added an onsite module that allows you to check\ **out** individual students (in the case where a student is leaving for lunch, etc.) or all students (in the case where the day has finished and you want to record checkin again for the next day). The module also allows admins to unenroll students from the classes that will be missed when they are checked out from the program. Checked out records will be reflected on the website in a number of ways:

   - The onsite checkin page now lists when a student was checked in and checked out. Checkins or checkouts can now be undone on this page. Students can also be checked out from this page by unchecking the "Attending" box.
   - Checked out students are accounted for in the onsite attendance module (#2 above).
   - The barcode checkin page will not raise an error if a student is checked out (and will then check them back in).
   - Attendance numbers in the grid-based class canges and grid-based status pages are now based on attending students that are not checked out.
   - There are now new "Currently checked out students" and "Currently checked in students" options for the comm panel, arbitrary user list, and group text panel.
   - The teacher attendance page (#1 above) will mark a student as checked in again if they have been checked out.

Onsite Webapps
~~~~~~~~~~~~~~
We've added mobile-friendly interfaces for teachers and students for tools that are commonly used at Splash events. We are looking to continue to improve these interfaces, so please let us know if you have any feedback! We'll also be making an admin interface in the future.

1. The teacher interface, available at ``/teach/[one]/[two]/teacheronsite`` (if enabled), has a live schedule, Google maps of campus (with directions to classrooms if set up), section details (including email addresses), section rosters (with attendance functionality), and a page for the Splash teacher survey and student survey responses. If no surveys are set up, this navigation panel is hidden (the new survey creation page can be used to set this up).
2. The student interface, available at ``/learn/[one]/[two]/studentonsite`` (if enabled), has a live schedule (with class changes), Google maps of campus (with directions to classrooms if set up), a course catalog, section details for their enrolled classes, and an interface to fill out the student survey. If no survey is set up, this navigation panel is hidden (the new survey creation page can be used to set this up).

   - Note that students will not be able to see the classrooms for their enrolled classes or perform class changes until they are marked as attending the program (this can be changed with template overrides). We plan to allow for this to be changed with a tag setting in the future.
   - Also, for class changes on the student webapp, students are allowed by default to enroll in classes that have fewer enrolled students than capacity. You can change two tags to potentially allow students to enroll in classes that are not full based on program attendance or class attendance (see the attendance section above for the distinction between these two). The tags are as follows:

     i. 'switch_time_program_attendance': Set this tag to the time at which you'd like to start using program attendance numbers instead of enrollment numbers. The format is HH:MM where HH is in 24 hour time. After this time, if at least 5 students have been checked into the program, students will be able to class change based on program attendance numbers. If this is not set, program attendance numbers will not be used. 
     ii. 'switch_lag_class_attendance': Set this tag to the amount of minutes into a class at which you'd like to start using class attendance numbers if available (instead of enrollment or program attendance). This many minutes into a class block, if at least 1 student has been marked attending that class, students will be able to class change based on class attendance numbers. If blank, class attendance numbers will not be used.
  
     - Note that if the tags are set, the hierarchy is that class attendance will be used if available; program attendance will be used if class attendance is not available; enrollment will be used if program attendance is not available. 
     - Note for chapters that were using the beta version of the webapp previously: these new tags replace the old 'count_checked_in_only' tag.
    

Student Acknowledgement
~~~~~~~~~~~~~~~~~~~~~~~
Similar to the teacher acknowledgement module, this module will force students to agree to some conditions (e.g. a code of conduct) during student registration.

Generic program links
~~~~~~~~~~~~~~~~~~~~~
We've added the ability to use generic links that redirect to the most recent/current program of a given program type (the one that is latest in time). The links are of the form ``[site].learningu.org/[tl]/[one]/current/[view]``, where ``[site]`` is the specific chapter site; ``[tl]`` is "teach", "learn", "manage", "volunteer", or "onsite"; ``[one]`` is the program type (e.g. "Splash", "Sprout", "HSSP"); and ``[view]`` is the specific page/view (e.g. "teacherreg", "studentreg", "dashboard", etc). Further arguments can be included after the view if they are normally included for that view.

Program Creation and Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Simplified the interface to select modules when creating or modifying a program. Now users check boxes about what functions you need rather than choosing modules by name, and most modules are automatically selected.
- When creating a program, if you are charging for the program financial modules (including the financial aid application module) will be automatically enabled.
- Only relevant and non-redundant modules are displayed on the main program management page (admin portal).
- Added a page where you can modify all of the settings for a program (``/manage/[one]/[two]/settings``), including settings associated with the program itself, teacher registration, and student registration.
- Added a page where you can modify the tag settings for a program (``/manage/[one]/[two]/tags``), with documentation and defaults for every tag.
- Added a page where you can modify the global tag settings (``/manage/tags``), with documentation and defaults for every tag.

  - Note that program and global tag settings can be very sensitive. Use caution and make sure to test your setup whenever you change them!

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
- Admins can now checkout floating resources to teachers through the teacher check-in module. This module also now displays which floating resources haven't been returned since their classes ended.

Teacher registration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Links to class and teacher email addresses are now included for each class and section on the main teacher registration page.

Printables changes
~~~~~~~~~~~~~~~~~~
- Revamped student schedules. They are now in a portrait layout and include amount due, names of teachers for classes, and barcodes for check-in.
- The ``studentchecklist`` printable now updates the statuses in the checklist based on the website records for whether students have been checked-in, have paid, and have turned in forms.
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
- Overhauled the survey interface for students and teachers. These users will now be shown a list of survey components that they can fill out in any order. These components consist of independent surveys for each class the user is registered for (if there are any 'per_class' survey questions) and a general program survey (if there are any non 'per_class' survey questions). The former are available once each class has begun and the latter is available once any of the classes has begun.
- These built-in surveys are now shown in the student and teacher onsite webapp interfaces. Additionally, teachers can see survey responses for their classes in the teacher onsite webapp interface.
- Admins can now specify which students and teachers have access to the built-in program surveys with the tags "survey_teacher_filter" and "survey_student_filter". These tags will also be used to calculate the number of potential participants when displaying survey results.
- All survey questions are now bolded (previously some question types were not).
- Survey result histograms for countable questions now show the entire possible range of answers.
- The ``top_classes`` page for program surveys works again.
- Fixed survey dumps in cases where survey names had certain forbidden characters.
- All per-class survey results are now shown on the admin survey review page (before only numerical questions were shown). Also cleaned up the HTML and PDF versions of the admin survey review page, made them prettier, and made it possible to filter the HTML survey results to a particular teacher.

Theme changes
~~~~~~~~~~~~~
- Links on the barebones and bigpictures themes that previously said "Admin Home", now correctly say "Administration Pages" like other themes
- Fixed the fruit salad header for instances where the program name was very long and overlapped with the login information. Also changed styling associated with the login box to make things symmetrical (and removed the text "Hello,").
- Fixed the colors of the buttons presented when editing a QSD/editable text on the bigpicture theme. Button colors will also now properly change when updated in the bigpicture theme settings.
- Fixed the width of the class edit form and the teacher preview table in the bigpicture theme.
- Added a new admin bar to all themes that didn't have it before and modified the admin bar of themes that already had one. This admin bar has more helpful links for admins and current program section(s).
- Added links to the LU `Privacy Policy <https://www.learningu.org/about/privacy/>`_.

Minor new features
~~~~~~~~~~~~~~~~~~
- You can now include unreviewed classes in the scheduling diagnostics.
- You can now sort the results of a user search. The results also now include the last program for which a user has a profile (has registered).
- The teacher major and affiliation fields are now included as options in the arbitrary user list module.
- Phase Zero (Student Lottery) is no longer included in the student registration checkboxes interface.
- More details are now included on the student lottery confirmation page, including information about their lottery status and the student's lottery group if they are in one.
- The student lottery can now support lottery groups of any size (specified by the "student_lottery_group_max" tag). If the tag is set to 1, options to join groups will not be shown to students.
- The teacher availability search bar now only searches teachers (for the autocomplete). The rapid check-in and formstack medical/liability student search bars now only search students (for the autocomplete).
- Added a new page where admins can check the status of comm panel emails (``/manage/emails/``).
- Moved the grade change request link in the profile form to just under the grade field.
- Profile form now is more specific about whose contact info is being collected. Student phone numbers can be left blank if the tag "require_student_phonenum" is set to "False."
- Added "View on site" links to a number of user-related pages in the administration pages.
- Added duration-from-now labels next to deadline form fields.
- Made the text on the profile form clearer when users can not change their grade/dob.
- Added emailcodes to the subjects of all emails to class/section lists (i.e. "[prefix] [emailcode] Subject"). The prefix can be changed in the admin pages (and will be omited from the subject if not set).
- Changed the theme of the administration pages. Each section on the main page is now moveable, collapsible, and closable.
- Added credit card transaction IDs to the Credit Card Viewpay Module.
- Added global tags to change the options for the shirt size (one tag each for teachers, students, and volunteers), shirt style (universal tag), and food preference (only applicable to students) profile form fields.
- Added a big board to the phase zero management page to track student lottery registration over time.
- Added an option to supply a list of winners for the phase zero student lottery (instead of the default random algorithm).
- Moved the schedule snippets that you can include in comm panel emails to templates, allowing them to be overriden.
- Added a class registration filter to the comm panel, group text, and arbitrary user list modules.
- Added tags "student_profile_hide_fields", "volunteer_profile_hide_fields", "educator_profile_hide_fields", and "guardian_profile_hide_fields" that allow any fields in the profile forms to be hidden (except for email address all profile forms and grade for the student profile form).
- Made the scheduling diagnostics page more user-friendly and prettier.
- Line item options can be marked "is_custom" meaning students can enter a custom cost.
- Students can now enter a custom donation amount in the donation module.

Minor bug fixes
~~~~~~~~~~~~~~~
- The debug toolbar remains active (if specified in a URL by the admin with "?debug_toolbar=t") when morphing into users.
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
- Removed all mentions of "Cybersource" in the Credit Card Viewpay Module to reduce confusion.
- Fixed /myesp/onsite for admins.
- The contact form now uses the organization short name for the teacher option.
- Added a dummy folder for survey histograms. This preemtively fixes any problems sites might have with saving the histogram files.
- Fixed the completion certificate printable and added blank default letterhead.
- Fixed the calculation of a section's capacity for cases where a section takes place in multiple classrooms.

Minor bug fixes and new features released in August 2020
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a link to the nametags page from the "All Printables" page.
- Fixed the "seq" value of the teacher onsite module and any related module objects (from -9999 to 9999). This stops it from popping up when a teacher tries to register for a program.
- Fixed the resizing of names on nametags (names will now be larger if there is space).
- Fixed the behavior of the +/- signs on flags on the manage class, class search, and teacher checkin pages.
- Fixed the registered teachers line on the teacher big board.
- Fixed a bug where classes without teachers would be counted towards teacher statistics on the teacher big board.
- Fixed the all classes spreadsheet for cases where field values had non-ascii characters.
- Improved spacing and appearance of the new program creation form and errors.
- Improved appearance and workflow of the program resources page.
- Improved spacing on the attendance page, added links to userview page.
- Added tag-controlled shirt and comment fields to the volunteer signup form.
- Fixed spacing of survey questions and answers, especially in the webapps.
- Fixed some survey management bugs.
- Fixed URLs in the admin and user custom form interfaces.
- Added answer labels to the survey review page.
- Class attendance (on the normal, onsite, and webapp pages) is now recorded live, not upon form submission (like teacher check-in).
- Fixed instances where the arbitrary user list broke when selecting guardian fields.
- Fixed the grade range popup on the teacher class registration page (depends on the 'grade_range_popup' program tag).
- Fixed the spacing on the theme select page.
- Added links on the class search page that direct to the comm panel, arbitrary user list, and group text modules (with filters applied).
- Reworked and condensed all of the links at the top of the class search page.
- Split the 'webapp_isstep' tag into two tags, 'student_webapp_isstep' and 'teacher_webapp_isstep', which are used for their respective registration modules.
- Classrooms are now sorted using natural sorting on the resources page and in the ajax scheduler.
- Fixed treatment of "Accepted (but Hidden)" classes and sections in various places.
- Distinguished between classes and sections with status "Cancelled" and status "Rejected" in various places.
- Split the survey module into separate teacher and student survey modules (this shouldn't have any front facing effects).
- Added tags 'student_survey_isstep' and 'teacher_survey_isstep' to add the respective survey modules as steps to registration (defaults are False) once the event has begun. If there is a student survey, the teacher survey module also gives a link to the survey review page.
- The grid-based class changes table is now re-rendered when the settings are changed and classes are hidden/shown to avoid lots of empty space in the table.
- The grid-based class changes page now allows you to enroll students in full classes without overriding capacities as long as program or class attendance numbers are below capacity if the proper tags are enabled (see the 'switch_time_program_attendance' and 'switch_lag_class_attendance' tags under the 'Onsite Webapps' section above.
- Added dummy data for the survey management pages to fix the rendered display of favorite class questions.
- Added functionality to send an email to the student whenever a financial aid request is approved (whether it be through the financial aid approval module or the admin pages).
- Made it clearer visually that you can click class titles to see the class information on the teacher check-in page.
- Added styling to the scheduling checks page to indicate which checks have returned problems.
- Added "Edit Class" and "Catalog Preview" links to the manage class page; added document and website info to the manage class page.
- Cleaned up the layout of the program directory/main management page.
- Modified the availability override setting on the ajax scheduler to make it harder to abuse/forget.
- Fixed various bugs related to the grid-based class changes page.

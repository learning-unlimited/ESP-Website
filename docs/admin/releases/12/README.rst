============================================
 ESP Website Stable Release 12 release notes
============================================

.. contents:: :local:

Changelog
=========

Attendance
~~~~~~~~~~
We've implemented a set of tools for teachers and admins to manage student class attendance:

1. We've added a new page ``/section_attendance`` that allows teachers to take attendance for a particular section (including unenrolled students). Teachers can either use a checkbox interface or scan barcodes (with their phones) like at student check-in to mark students as attending the class. Options are provided to allow teachers to enroll students in their class if they were not previously enrolled. The page is linked to from the main teacher registration page (for sections that are approved and scheduled). The page has a dropdown menu for the teacher to select one of their sections for attendance.
2. We've also added an onsite module that summarizes attendance statistics/details. The page has a similar dropdown to select a particular timeslot for attendance. The page is linked to from the main onsite page (provided the module is enabled).

Generic program links
~~~~~~~~~~~~~~~~~~~~~
We've added the ability to use generic links that redirect to the most recent/current program (the one that is latest in time). The links are of the form ``[site].learningu.org/[tl]/[one]/current/[view]``, where ``[site]`` is the specific chapter site; ``[tl]`` is "teach", "learn", "manage", "volunteer", or "onsite"; ``[one]`` is the program type (e.g. "Splash", "Sprout", "HSSP"); and ``[view]`` is the specific page/view (e.g. "teacherreg", "studentreg", "dashboard", etc). Further arguments can be included after the view if they are normally included for that view.

Onsite changes
~~~~~~~~~~~~~~
- You can now customize the teacher check-in text message in a template override (``program/modules/teachercheckinmodule/teachertext.txt``)
- When texting all unchecked-in teachers through the teacher check-in page, you can now opt to skip teachers of classes with at least one checked-in teacher.

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

Scheduler changes
~~~~~~~~~~~~~~~~~
- Room requests are now included in the scheduler.
- You can now filter classrooms (rows) in the scheduler by room capacity, resource, and name.
- Added an option in the "Class Filters" tab to override teacher availability when scheduling classes. This will NOT override lunch constraints, already scheduled classes, or whether a class will actually fit time-wise where you are trying to schedule it.
- The scheduler now works even if the Teacher Availability Module is not enabled (teachers will have full availability).

Flag and classsearch changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Flags are now in a separate category on the dashboard (and are prettier).
- Newly created flags no longer disappear when you click on their header.
- Clickable items (such as flags and class titles) are now more obvious and neater on the classsearch page and other places flags are shown.
- Flag names are now shown on the teacher checkin page without having to expand the class. Clicking on the flag names reveals the flag details.
- Added a class flag printable.

Minor new features
~~~~~~~~~~~~~~~~~~
- You can now include unreviewed classes in the scheduling diagnostics.
- You can now sort the results of a user search. The results also now include the last program for which a user has a profile (has registered).
- The teacher major and affiliation fields are now included as options in the arbitrary user list module.
- Phase zero is no longer included in the student registration checkboxes interface. More details are now included on the lottery confirmation page.
- Histograms for numerical questions in the built-in surveys now show the entire possible range of answers
- The teacher availability search bar now only searches teachers (for the autocomplete). The rapid check-in and formstack medical/liability student search bars now only search students (for the autocomplete).
- Added a new page where admins can check the status of comm panel emails (``/manage/emails/``).
- Moved the grade change request link in the profile form to just under the grade field.

Minor bug fixes
~~~~~~~~~~~~~~~
- The debug toolbar remains active (if specified by the admin) when morphing into users.
- All required fields are now marked as such in the profile form.
- Cancellation emails now permit symbols, such as apostrophes.
- The ``top_classes`` page for program surveys works again.
- The background for the userview page will always be at least as long as the content on the page.
- Fixed survey dumps in cases where survey names had certain forbidden characters.
- You can now actually sort the classes on the dashboard by many fields.
- Fixed a bug that allowed teachers to see the rosters for any sections/classes, even if they weren't teachers for them.
- Fixed some bugs in the class catalog related to hiding classes and registration buttons. Unscheduled sections are now considered "Full".
- Fixed a bug where sections weren't completely unscheduled when their classrooms were deleted.
- Fixed a bug where admins would need to flush the cache after changing the lunch constraints to make them update in the scheduler.
- Fixed many instances where a student's grade was listed as the current grade but should have been the grade at the time of the program.
- The grade change request link is no longer displayed in the profile form for new users or users that can change their grade in the form.

Known issues of new features
============================

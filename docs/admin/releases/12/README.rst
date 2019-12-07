============================================
 ESP Website Stable Release 12 release notes
============================================

.. contents:: :local:

Changelog
=========

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

Scheduler changes
~~~~~~~~~~~~~~~~~
- Room requests are now included in the scheduler.
- You can now filter classrooms (rows) in the scheduler by room capacity, resource, and name.

Flag and classsearch changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Flags are now in a separate category on the dashboard (and are prettier).
- Newly created flags no longer disappear when you click on their header.
- Clickable items (such as flags and class titles) are now more obvious and neater on the classsearch page and other places flags are shown.

Minor new features
~~~~~~~~~~~~~~~~~~
- You can now include unreviewed classes in the scheduling diagnostics.
- You can now sort the results of a user search. The results also now include the last program for which a user has a profile (has registered).
- The teacher major and affiliation fields are now included as options in the arbitrary user list module.
- Phase zero is no longer included in the student registration checkboxes interface. More details are now included on the lottery confirmation page.
- Histograms for numerical questions in the built-in surveys now show the entire possible range of answers
- The teacher availability search bar now only searches teachers (for the autocomplete). The rapid check-in and formstack medical/liability student search bars now only search students (for the autocomplete).
- Added a new page where admins can check the status of comm panel emails (``/manage/emails/``).

Minor bug fixes
~~~~~~~~~~~~~~~
- The debug toolbar remains active (if specified by the admin) when morphing into users.
- All required fields are now marked as such in the profile form.
- Cancellation emails now permit symbols, such as apostrophes.
- The ``top_classes`` page for program surveys works again.
- The background for the userview page will always be at least as long as the content on the page.
- Fixed survey dumps in cases where survey names had certain forbidden characters.
- You can now actually sort the classes on the dashboard by many fields.

Known issues of new features
============================

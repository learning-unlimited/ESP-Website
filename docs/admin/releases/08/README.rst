============================================
 ESP Website Stable Release 08 release notes
============================================

.. contents:: :local:

Changelog
=========

New AJAX scheduler
~~~~~~~~~~~~~~~~~~

The AJAX Scheduling module has been completely rewritten for improvements to usability and maintainability. Major new features include improved color-coding for possible class placements, clicking to select and place classes instead of drag and drop, and locking to prevent other admins from accidentally moving a class.

Instructions for using the scheduler:

- Click on the class you want to schedule (either in the directory or on the grid) to select it.
- On the grid, the places you might put the class are highlighted. Legend:
 - Green means you can put the class there.
 - Green with stripes means the class can't start there, but there should be a green square to the left where you can place it (for multi-hour classes).
 - Yellow means the teacher is available then, but teaching another class.
- Click on a green highlighted square to place the class. Click anywhere else on the grid or directory to unselect the class.
- When you have a class selected, the pane in the upper right corner displays info about the class as well as links to the manage and edit pages.
- When no class is selected, the pane in the upper right corner displays scheduling errors.
- Hovering over a room cell or a class section gives you a tooltip with info about the classes.
- The lower right pane is the directory. You can search using the search bar at the top and select how you want to search with the radio buttons. You can move to the filters tab of the directory and set bounds on different parameters such as capacity and length.
- To set a comment on a class's scheduling, select it and click on "Set Comment" in the upper right pane. A dialog for entering a comment will appear.
- To lock a class, follow the instructions to set a comment, and check the "Lock" box in the comment dialog. A red border will appear around it in the schedule or directory, and no one will be able to move it without unlocking it first. To unlock a class, select it and then click on "Edit Comment or Unlock". Any admin can lock or unlock any class.

Keyboard shortcuts:

- ESC unselects the currently selected class
- F1 switches to the directory tab
- F2 switches to the filters tab
- / selects the search box
- DEL unschedules the currently selected class

Unenroll absent students
~~~~~~~~~~~~~~~~~~~~~~~~

In the past, MIT has run a script to find students who haven't checked in before their first class and unenroll them from their future classes. This functionality is now available as a program module. To use it, add the "Unenroll Students" module to your program, and then click on the "Unenroll Students" link from the main onsite page. The page allows you to select the set of registrations to remove.

Per-grade program caps
~~~~~~~~~~~~~~~~~~~~~~

The site now supports having per-grade program caps.  The backend for program caps has also been updated, so the logic should be more consistent and correct.

As before, the overall program cap is controlled by setting "Program size max" in the admin panel for the program.  Per-grade caps override this setting, and are controlled by the Tag ``program_size_by_grade``, generally set on a specific program.  The value should be a JSON object; the keys should be strings, either individual grades (as strings, e.g. "7"), or ranges (e.g. "7-9"), and the values should be nonnegative integers.  These ranges should cover all grades for which you want to have a cap.  If you want, they can be overlapping, but that will probably cause worse performance for students in the overlap, since it will have to check both grades.  So it should look something like ``{"7-8": 1000, "9": 300, "10-12" 1500}`` if you want to allow 1000 total 7th and 8th graders, 300 9th graders, and 1500 total 10th-12th graders.

Note: all program caps, and especially per-grade ones, will hurt your site's performance, because we need to check how many students are in the program every time a student tries to join it.  If you don't intend to set a program cap, just leave the field blank, and you'll get much better performance than setting it to a large value.

Class search improvements
~~~~~~~~~~~~~~~~~~~~~~~~~
With this release, class search allows you to edit your search at the top of the search page.  The results page also includes a new button to email the teachers of a class, a new button to show all classes and all flags which have comments, and an option to randomize the order of search results, along with a minor bugfix.

Onsite print schedules page diagnostic information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The onsite print schedules page now shows a list of the most recent print requests. This should help with figuring out what's wrong if printing isn't working as expected.

User search improvements
~~~~~~~~~~~~~~~~~~~~~~~~
With this release, the User Search box returns users whose cell phone number or
*parent's* email address matches the query, in addition to the matches that were
previously returned. The search is also more robust to case and whitespace issues.

Minor new features and fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Other improvements in this release include:

- The onsite landing page now has a link to the scrolling class list

- Bug in SR07 where form validation errors in teacher profiles could cause a server error is fixed

- Server error when user searching empty string is fixed

- Server error on manage or edit page for nonexistent class is fixed

- Number of students attending program is now available on the studentreg big board

- Student profile module will now correctly show "not a student" error instead of deadline error

- Teachers will only see "class is full" if at least one section is scheduled

- Display improvements to fruitsalad bubblesfront page and editable text attribution line

- Display improvements to alerts on volunteer signup page

- Fixes for display bugs in the onsite class changes grid

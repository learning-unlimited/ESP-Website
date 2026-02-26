============================================
 ESP Website Stable Release 04 release notes
============================================

.. contents:: :local:

Changelog
=========

Schema Simplification
~~~~~~~~~~~~~~~~~~~~~

In this release, we made a major architectural change in how we store
program-related information in the database. This particular project introduced
no front-end behavioral changes. However, it did involve updating a significant
percentage of our code, which means there are many potential sources of bugs.
We believe everything works, but we may discover features that are broken
because of an improperly coded upgrade to the new schema. As such, please make
sure to test all parts of the website before you need them.  Don't assume,
until you have tested it, that an important feature that worked last year will
still work now. Report any bugs you find, and we will fix them ASAP.

If you previously knew about User Bits and the Data Tree, or if you are
otherwise interested in the scope of these changes, read
`<schema_simplification.rst>`_.

Themes - front end design
~~~~~~~~~~~~~~~~~~~~~~~~~

To simplify front end design, there is now an app for configuring the front end
(appearance and navigation) of your site.  It can be accessed at /themes/.  You
can select from pre-defined themes (/themes/select), configure page contents
(/themes/setup), or adjust aesthetic parameters (/themes/customize).  Behind
the scenes, the app is generating template overrides and CSS stylesheets based
on your configuration.  More details can be found at
`</docs/admin/themes.rst>`_ or
`<http://wiki.learningu.org/Generic_Templates>`_.

Check Availability Page
~~~~~~~~~~~~~~~~~~~~~~~

If you add the "Check Teacher Availability" module for your program, the
page at /manage/[program url]/check_availability will allow you to see a
teacher's availability for that program. It shows all of the program's
timeslots in order, and colors each one based on the teacher's status. Gray
indicates unavailable, blue indicates available, black indicates available and
already scheduled to teach, and orange indicates scheduled to teach but not
marked as available, which probably means something went wrong.

The name and room of each of the teacher's scheduled classes are shown below
the corresponding timeslot, and the name and duration of each of the teacher's
unscheduled classes are shown in a list at the bottom of the page.

This page can also be accessed by clicking "Show Complete Module List" and then
"Check Teacher Availability" on the program's manage page.

Userview Page
~~~~~~~~~~~~~

The page at /manage/userview?username=[username] (accessible from the "user
search" widget visible in the left corner of any page if you are logged in as
an administrator) shows information about users on the website. The page has
been redesigned, featuring selectable email addresses, and buttons to take
various actions on a user that are useful before and during a program. From
here:

- "Morph into this user" temporarily logs you in as that user, to view the
  website from that user's perspective.

- "Onsite for [program]" allows you to access the onsite class changes portal
  for a student, to add and remove classes from the student's schedule.

- "Student schedule for [program]" allows you to view and print a student's
  schedule for the most recent program. There are several options: "print
  locally" pulls up the schedule in your browser; if you have set up printing
  through the website, you will also see a "print to [printer]" option for each
  printer available.

- For teacher users, "Teacher schedule for [program]" allows you to view a
  schedule showing all the classes a teacher is teaching.

All of this functionality can be quickly accessed by using the "user search"
widget, visible in the left corner of any page if you are logged in as an
administrator. You can search for any user by name, username, or user ID
number.

Scheduling Checks Program Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the "Scheduling Diagnostics" module to your program, and you will see a
link to "Run Scheduling Diagnostics"
(/manage/[program]/[instance]/scheduling_checks) on the main program management
page.  This page may take a few minutes to load, but when it does it will
provide information on potential problem classes (inappropriate classrooms or
resources, not enough time) and teachers (scheduling conflicts, admins
teaching, back-to-back classes in different rooms).  We recently added the
check for "hungry teachers" (those who are teaching during lunch), and
corrected some errors in the diagnostic output.

Class flags
~~~~~~~~~~~

This is a new feature for tracking the review of classes.  The idea is that you
can create various types of class flags, like "needs safety review" or
"description has been proofread", and then get a list of classes with (or
without) some set of flags.

To set up class flags, first add some flag types from the admin panel at
/admin/program/classflagtype/, then add them to your program by choosing your
program in /admin/program/program/ and scrolling to the bottom of the page.
(There is also a place to add them at program creation.) Now you can add and
view class flags from the edit class or manage class pages.  To create a list
of classes with(out) some flag, go to the manage page for the program, and in
the complete list of modules, choose "Manage class flags".

This is still a work in progress; everything should work fine, but if there are
more interfaces you would like to see, let the web team know!

Emailing Program Guardians From the Communications Panel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The communications panel can now send mail to the listed guardian and emergency
contact email address for students. On the first screen of the commpanel
(/manage/<program>/<instance>/commpanel), after you select that you are
emailing students, you can select which combination of students, guardians, and
emergency contacts you wish to address. On the next screen, you can narrow down
your query (for example, for all students who are enrolled in the program).
When you send the message, it will go to the types of contacts (students and/or
guardians and/or emergency contacts) that you specified.

Accounting System
~~~~~~~~~~~~~~~~~

The administrative interfaces for financial aid and payments have changed.  To
review financial aid applications, go to "Financial aid requests" under
"Program"; if you would like to grant financial aid, fill out the form at the
bottom of the page under "Financial aid grant."  To change the costs for a
program, go to "Line Item Types" under "Accounting."  You can change the
"amount_dec" field on the "Program Admission" type.  If you would like to offer
items for purchase via the "Student Extra Costs" program module, you can create
additional line item types for your program and set the "Max quantity" field
appropriately; do not check the "for payments" or "for finaid" boxes.  If you
are using the "SplashInfo Module" to offer lunch, the size of the sibling
discount is set as a line item type, but the lunch options and their costs are
still controlled by the splashinfo_choices and splashinfo_costs Tags.  Items no
longer have a separate cost for financial aid students; the amount these
students are charged is determined by the financial aid grant.

All transactions appear as "Transfers" under "Accounting" in the admin
interface. Transactions move money from one account from another.  By default,
you are given one account for each program and three global accounts
(receivable, payable, and financial aid).  The balance of an account is the sum
of the incoming transfers minus the outgoing transfers; you can see the balance
of each account at /accounting/.

Please let us know what accounting functionality you would like to see added or
changed in the next release.  If you would like to use credit cards to collect
payments, please contact us.

Redirects
~~~~~~~~~

You can create redirects from/to arbitrary URLs. For example, I can make /lu
redirect to https://learningu.org, and I can make /splashstudentreg redirect to
/learn/Splash/2013_Fall/studentreg. The interface to create redirects is at
/admin/redirects/redirect/.  You may want to use this to create "clean" URLs
for publicly accessible media files (such as liability and medical forms) or
URLs you expect people to type (such as /survey for a student survey, when you
want to print a link on student schedules).

Class Cap Multipliers
~~~~~~~~~~~~~~~~~~~~~

The website allows you to specify a multiplier and constant offset for class
capacities in each program. This option is disabled by default. If you want to
use it, there are two different options: multiply/offset each section's
capacity as specified by the teacher at teacher registration, or
multiply/offset room capacity for this program only. These are useful if you
want to account for the fact that many students register and then don't show up
to programs, leaving even popular classes with empty spots. The option to
affect room capacity instead of the teacher's chosen section capacity was
recently added as a way to avoid the risk of too many students showing up to a
materials-limited class by only relaxing constraints imposed by rooms.

To change these options, go to /admin/modules/studentclassregmoduleinfo/ and
click on the link for your program. Type the multiplier and offset into the
respective boxes. For example, type 1.1 and 5 to increase each class or room
size by 10% plus 5 additional spots. If you want to use the option to affect
room capacity instead, check the "Apply multiplier to room cap" box.

Formstack Medical
~~~~~~~~~~~~~~~~~

The website has a pair of modules that direct students to an external site to
submit medical information before they can continue with registration. The
modules are "Formstack Med-liab Module" and "Formstack Med-liab Bypass Page"
(the latter allows administrators to grant a "bypass" to students, allowing
them to opt-out of online submission). A separate program, hosted at
`<https://github.com/btidor/esp-medical>`_, is used to collect the encrypted
information and store it locally. If your chapter is considering implementing
online collection of medical information, please talk to MIT ESP at
esp-webmasters@mit.edu for aid and suggested security considerations.

AJAX Scheduler upgrades
~~~~~~~~~~~~~~~~~~~~~~~

Numerous improvements have been made to the AJAX class scheduler. These are
outlined below.

- Two-column user interface: this increases the vertical space so that more
rooms are displayed, and the frames are resizable.

- Changelog: a changelog of scheduled classes is stored in the database. This
is used to facilitate periodic incremental updates on the client-side interface
of the scheduling matrix (currently every ten seconds). Synchronization between
multiple users works decently.

- Filtering: several filtering modes exist now that can be used to filter the
list of classes. This is accessible from the right-hand-side frame.

Two-phase student registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a new mode of student registration which functions much like the lottery
(in the back-end) but has a new front-end interface.  In the first step,
students are asked to "star" the classes they are interested in, using a
searchable interactive catalog.  In the second step, students can select which
classes to mark as "priority" and which to mark as "interested" for each time
slot.

To make use of this module, enable Two-Phase Student Registration from the admin
panel. This module will replace the student registration landing page (the page
with the checkboxes) until it is disabled. This is something we would ideally
fix in a future release, but for now the recommended workflow is to enable the
module for the Two-Phase portion of registration, then disable it and allow
students to land at the normal landing page to complete registration and change
classes after the lottery has been run.

Full documentation can be found in the program modules docs:
`</docs/admin/program_modules.rst#two-phase-student-registration-studentregtwophase>`_.

Markdown Version Upgrade
~~~~~~~~~~~~~~~~~~~~~~~~

Markdown, the software package that we used to render the quasi-static content,
has been upgraded to the latest version, 2.3.1
(`<https://pypi.python.org/pypi/Markdown/2.3.1>`_). This may have affected the
visual appearance of your existing pages. Please double-check your web-content
throughout the site to ensure that it appears correctly. The documentation for
Markdown syntax is at `<http://daringfireball.net/projects/markdown/syntax>`_.

Teacher training creation and sign-up
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An interface for teacher training and interviews management has been added,
accessible from Program manage page -> Complete module list -> Teacher Training
and Interviews. Once there, the page has a form with instructions that allows
the creation of a teacher training or interview. As before, the same page
displays a list of users who have signed up for a given slot.

Open classes (walk-in seminars/activities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some programs have been hosting open classes or walk-in seminars, which operate
in parallel with normal classes; information about them is displayed on the Web
site, but students cannot register for them.  Examples of walk-in seminars
include card games, origami, or other activities without a fixed schedule or
curriculum; students may come and leave at any time.

To allow open classes, you can create a category for them ("Class categories"
under "Program" in the admin interface).  Make sure that this category has been
added to the list of categories for the program.  Associate this category with
"open classes" by creating an open_class_category Tag, whose value is the ID of
the specific category you are using (an integer). You must also select "Open
class registration" for the program's ClassRegModuleInfo object, which you can
edit from /admin/modules/classregmoduleinfo/.

Teachers can create an open class (as opposed to a normal class) by clicking
"Add a new [category name] for this program…" on the main teacher registration
page.  If you allow teachers to create these classes, please provide them with
explicit instructions on the differences between these and normal classes.

Program email addresses
~~~~~~~~~~~~~~~~~~~~~~~

The director email address option has been split up into three mailing lists in
this release: a normal director address used for most communications and
displayed on the website, a confidential address used for private data
(currently only financial aid requests), and a carbon-copy email that is
included in class registration, class change, and interview registration
notifications. If either or both of the latter two are not set, then the main
director address is used instead as a default.

Class status button on dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the dashboard next to each class there exists a "Status" button, in addition
to the "Delete", "Edit", and "Manage" buttons. This is a quick interface for
updating the status of the class without having to load a new page. Clicking
"Status" brings up a pop-up with the class vitals: current status, logistical
details, description, prerequisites, and grade range. At the bottom are the
options to approve the class as a whole, reject the class as a whole, or mark
it unreviewed (if it was previously approved or rejected). If going through
lots of classes and approving before a program, we can use this to keep the
dashboard page loaded and scroll through approving a class at a time without
having to load any new pages.

Versioned QSD
~~~~~~~~~~~~~
QSD pages are now versioned, so that changes can be tracked, old versions can
be accessed, and you can revert if necessary. The versioning can be managed
from Admin Panel (/admin) -> Quasi static datas. To recover a deleted QSD, use
"Recover deleted quasi static datas" in the top right. To view the changelog,
select a QSD page (you can search by URL or title) and select "History" in the
top right. To revert to an old version of the page, select a version from the
History page and press Save at the bottom.

Uploading / managing media files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We are no longer using Dropbox to share media files with admins.  If you would
like to customize your images and stylesheets, or manage uploaded files, you
now have full control through your site's admin interface.  Go to
/admin/filebrowser/browse/.  The server has the only authoritative copy of
these files; the Dropbox accounts will be closed following the release.

Smarter user autocomplete
~~~~~~~~~~~~~~~~~~~~~~~~~

User autocomplete fields no longer expect the format "Last, First". You can now
search "Last, First" or "username" or "user_id".

Allow full-page letterhead
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can now use arbitrary letterhead for the "student completion letters"
(accessible from program printables).  It should be a full-page-sized PDF file,
uploaded to /esp/public/media/latex_media/letterhead.pdf (this should be
accessable from the new filebrowser, by clicking on "latex_media" then
uploading it as letterhead.pdf). That said, there are still some issues with our
LaTeX generation scripts that may get in your way; we'll be working on fixing
those for the final version of the stable release.

Obfuscated uploaded file names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A set of allow file extensions is defined to prevent XSS attacks, and files can
now be downloaded with the original filename again. These changes are
transparent to users -- the old /download/file_hash URL's still work and the
new URL's are displayed on documents pages.

Grade change requests
~~~~~~~~~~~~~~~~~~~~~

Students can now request to have their current grade changed through the
website, by filling out the new grade and a reason that it needs to be changed.
The page to do this is /myesp/grade_change_request.
After the student confirms the change, an email will be sent to the admin
contact address notifying that the change was requested. An admin page exists
where admins can approve the requests (after which an email will be sent to the
student notifying them of the approval).

Minor feature additions
~~~~~~~~~~~~~~~~~~~~~~~

- The number of students who applied to a class in the lottery is now visible
  in the "status" popup on the program dashboard.

- You can ask for students' gender on the profile form by enabling the
  'student_profile_gender_field' Tag.  This feature is disabled by default.

- The user view page now shows the times of each class a student is taking.

- The main teacher registration page makes the approval status of classes more
  clearly, so that teachers only see section information if their class is
  approved.

- The notification emails sent out when teachers register or edit classes now
  has a link you can click to directly approve the class.

- When importing classrooms from a previous program, you can now specify that
  all classrooms should be available for all of the timeslots of the new
  program, instead of trying to match up timeslots from one program to the next.

- You can now import timeslots from a previous program, specifying only the
  start date of the new program.

- The US Zip codes are now populated by default, so new sites can send emails
  based on location without any additional setup.

- The "User list generator" program module now uses the newer interface that
  was provided for the comm panel in the last stable release.

- Mass emails (i.e., emails sent from the communication panel) will now be
  resent if the first attempt fails, and failure reports will be sent to the
  director email. Some other stability changes made too.

- The dashboard now shows some new statistics: the "Categories" section now
  includes the number of class-hours per category, and there is a new "Grades"
  section that shows the number of students per grade enrolled in at least one
  class and number of subjects and sections available to the students in that
  grade.

- You can now filter for students in particular grades using the comm panel.
  The grade filtering options will show up at the bottom of the list (below
  "States" and "School") on step 3 when you are creating a list of students.
  You will also see an option to filter teachers by graduation year.

- Credit card transaction refunds are now easier to accomplish as the credit
card transaction ID is now stored in the transaction model.

Django debug toolbar (developers only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are running a development site, a developer toolbar will appear on the
right side of your screen.  This toolbar allows you to view the SQL queries
incurred by the page load (helpful for improving performance) and which
templates were used, among other things.  You can enable or disable it via the
debug_toolbar GET variable, for example http://localhost:8000/?debug_toolbar=f,
or with the DEBUG_TOOLBAR setting in local_settings.py.  There are more
configuration options defined in django_settings.py.  For more information see
`<http://django-debug-toolbar.readthedocs.org/en/1.0/>`_.

virtualenv (developers only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The code has been modified to utilize a virtual environment for Python files.
The virtualenv is a requirement for external scripts, and it is recommended
that web servers running ESP-Website now be configured to also utilize the
virtual environment. A script is included to automatically do the configuration
(specifically, make_virtualenv.sh).

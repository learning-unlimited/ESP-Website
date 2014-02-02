=================
Program modules
=================

.. contents:: :local:

When you create a program, your primary means of controlling the registration process is to choose which program modules to include.  Each program module corresponds to a "view" that users will be able (or perhaps compelled) to see when they are registering.  

You may select which program modules to include on the program creation form at http://[hostname]/manage/newprogram.  After a program has been created, you can select which modules to include within the administration pages; go to http://[hostname]/admin/program/program/, select your program and edit the "Program modules" multi-select field.

More background on program modules
==================================

Program modules are broken down into the following categories:

* Student modules - http://[hostname]/learn/[program]/[instance]/*
* Teacher modules - http://[hostname]/teach/[program]/[instance]/*
* Management modules - http://[hostname]/manage/[program]/[instance]/*
* Onsite modules - http://[hostname]/onsite/[program]/[instance]/*
* Volunteer modules - http://[hostname]/volunteer/[program]/[instance]/*

Once you associate a module with a program, a "program module object" is created that allows you to customize the module's behavior for that specific program.  These objects may be edited at http://[hostname]/admin/modules/programmoduleobj/. The following settings can be changed:

* seq (Sequence number) - Determines the ordering in which users see this module.  Modules are displayed in order of increasing sequence number.
* required - Check this box to make the module required.  If the module is required, users will be directed through its view before reaching the main registration page.
* required_label - A string may be entered here to clarify your requirements for the module beyond simply being "required" or "not required."  For example, you could uncheck the required field but set required_label to "Required for outside teachers" on the teacher biography module.

You will also see references to other data structures that store configuration settings relevant to program modules:

* [Teacher] module control (ClassRegModuleInfo): http://[hostname]/admin/modules/classregmoduleinfo/
* Student module control (StudentClassRegModuleInfo): http://[hostname]/admin/modules/studentclassregmoduleinfo/
* Tags: http://[hostname]/admin/tagdict/tag/ - Very powerful, but more advanced; see [[Customize behavior with Tags]] for more information.

Below we provide a more detailed explanation of what each program module is for and which settings can be used to adjust it.

Student modules (10)
====================

Core Student Reg (StudentRegCore)
---------------------------------

This module should be enabled if students will be registering using the Web site. It aggregates information and links to other other student modules that are enabled on the main registration page at http://[hostname]/learn/[program]/[instance]/studentreg. Settings affecting this module are: 

* Student module control field "Progress mode": Set to 1 to show registration steps as checkboxes, 2 to show registration steps as a progress bar, or 0 to not show them at all. 
* Student module control field 'Force show required modules': Check the box to show the student all required modules (e.g. profile editor, lunch/sibling information, etc.) before allowing them to proceed to the main registration page. If unchecked, the student can complete registration steps in any order but must finish all required steps before confirming their registration. 
* Student module control fields 'Confirm button text,' 'Cancel button text,' and 'View button text': You may enter text here to customize the labels shown on these buttons at the bottom of the main registration page. 
* Student module control field 'Cancel button dereg': If you check this box, students will be removed from all classes they registered for when they click the 'Cancel registration' button. 
* Student module control field 'Send confirmation': If checked, students will receive e-mail when they click the 'Confirm registration' button. You need to create an e-mail receipt as described here: [[Add a registration receipt]] 
* Tag 'allowed_student_types': Controls which types of user accounts may access student registration. By default, student and administrator accounts have access.

Student Class Registration (StudentClassRegModule)
--------------------------------------------------

This module should be enabled if your program involves students picking and choosing their classes. It is used to display the catalog, schedule, and class selection pages. Settings affecting this module are: 

* Student module control field 'Enforce max': Unchecking this box allows students to sign up for full classes. 
* Student module control fields 'Class cap multiplier' and 'Class cap offset': Allows you to apply a linear function to the capacities of all classes. For example, to limit classes to half full (perhaps for the first day of registration) you could use a multiplier of 0.5 and an offset of 0; to allow 3 extra students to sign up for each class you could use a multiplier of 1 and an offset of 3. 
* Student module control field 'Signup verb': Controls which type of registration students are given when they select a class. The default is "Enrolled," which adds the student to the class roster (i.e. first-come first served). However, you may choose "Applied" to allow teachers to select which students to enroll, or create other registration types for your needs. 
* Student module control field 'Use priority': When this box is checked, students will be allowed to choose multiple classes per time slot and their registration types will be annotated in the order they signed up. This is typically used with the 'Priority' registration type to allow students to indicate 1st, 2nd and 3rd choices. 
* Student module control field 'Priority limit': If 'Use priority' is checked, this number controls the maximum number of simultaneous classes that students may register for. 
* Student module control field 'Register from catalog': If this box is checked, students will see 'Register for section [index]' buttons below the description of each available class in the catalog. If their browser supports Javascript they will be able to register for the classes by clicking those buttons. You will need to add an appropriate fragment to the QSD area on the catalog if you would like students to see their schedule while doing this. 
* Student module control field 'Visible enrollments': If unchecked, the publicly available catalog will not show how many students are enrolled in each class section: 
* Student module control field 'Visible meeting times': If unchecked, the publicly available catalog will not show the meeting times of each class section. 
* Student module control field 'Show emailcodes': If unchecked, the catalog will not show codes such as 'E464:' and 'M21:' before class titles. 
* Student module control 'Show unscheduled classes': If unchecked, the publicly available catalog will not show classes that do not have meeting times associated with them. 
* Student module control 'Temporarily full text': You may enter text here to customize the label shown on disabled 'Add class' buttons when the class is full. 
* Tag 'studentschedule_show_empty_blocks': Controls whether the student schedule includes time slots for which the student has no classes. By default, empty blocks are displayed.

Student Profile Editor (RegProfileModule) 
-----------------------------------------

This module should be enabled if you would like students to fill out their profile form as part of the program registration process. The profile form includes contact information for the student, parent and emergency contact, as well as student-specific information like "how you heard about Splash?" and "what school do you go to?". 

It is required by default when enabled. However, if a student has filled out a profile within the previous 5 days (e.g. for a newly created account), their previous profile will be duplicated and they won't have to fill it out again. 

Relevant settings include: 

* Tag 'schoolsystem': Controls whether students are prompted to enter the ID number for their local school system, and if so, how that part of the form should work. <br> 
* Tag 'require_school_field':&nbsp;Controls whether the 'School' field is required.<br> 
* Tags 'require_guardian_email' and 'allow_guardian_no_email':&nbsp;Controls whether students have to enter their parent's e-mail address.&nbsp; If 'allow_guardian_no_email' is set, then students can check a box saying "My parents don't have e-mail" to make the e-mail field non-required.<br> 
* Tag 'request_student_phonenum':&nbsp;Controls whether the student phone number field is required. 
* Tag 'allow_change_grade_level': By default, a student's graduation year is fixed after the first time they fill out their profile; this is intended to prevent students from lying about their age in order to get into certain classes. If this Tag is set, students may change their grade level at any time.<br> 
* Tag 'student_grade_options': A JSON-encoded list of grade choices can be used to override the defaults (7 through 12 inclusive). 
* Tag 'student_medical_needs': If tag exists, students will see a text box where they can enter 'special medical needs'. 
* Tag 'show_studentrep_application': If tag exists, the student-rep application is shown as a part of the student profile. If it exists but is set to "no_expl", don't show the explanation textbox in the form. 
* Tag 'show_student_tshirt_size_options': If tag exists, ask students about their choice of T-shirt size as part of the student profile 
* Tag 'show_student_vegetarianism_options': If tag exists, ask students about their dietary restrictions as part of the student profile 
* Tag 'show_student_graduation_years_not_grades': If tag exists, in the student profile, list graduation years rather than grade numbers 
* Tag 'ask_student_about_post_hs_plans': If tag exists, ask in the student profile about a student's post-high-school plans (go to college, go to trade school, get a job, etc) 
* Tag 'ask_student_about_transportation_to_program': If tag exists, ask in the student profile about how the student is going to get to the upcoming program<br>

More details on these Tags can be found here: [[Customize behavior with Tags]].

Financial Aid Application (FinancialAidAppModule) 

Text Message Reminders (TextMessageModule) 

Lottery Student Registration (LotteryStudentRegModule) 

Student Surveys (SurveyModule) 

Add "Confirm Registration" link (StudentRegConfirm) 

Splash Info (SplashInfoModule) 

Student Application (StudentJunctionAppModule)

== Teacher modules (11) == 

Core Teacher Reg (TeacherRegCore)

Teacher Signup Classes (TeacherClassRegModule)

Teacher Availability (AvailabilityModule)

Teacher Profile Editor (RegProfileModule)

Teacher Biography Update (TeacherBioModule)

Teacher Training and Interview Signups (TeacherEventsModule)

Teacher Logistics Quiz (TeacherQuizModule)

Teacher Class Previewing (TeacherPreviewModule)

Teacher Surveys (SurveyModule)

Application Reviews for Teachers (TeacherReviewApps)

Remote-Teacher Profile Editing (RemoteTeacherProfile)

Management modules (20)
=======================

Class Management For Admin (AdminClass)
---------------------------------------

It is recommended to include this module in all programs, since it includes frequently used functions such as deleting and approving classes that are used by other program modules.  Functions include:

* "Manage class" page, which is accessible from the list of classes on the program dashboard.  This page provides fine control over scheduling and co-teachers and allows you to open/close individual sections.  It also lets you cancel a class and e-mail the students.
* Reviewing (e.g. approving) classes, which can be done via a link in the class creation/editing e-mails.
* Bulk approval of classes by typing in their IDs.

AdminCore (AdminCore)
---------------------

You should include this module in all programs.  It provides the main program management page, from which you access all other management modules.  It also provides the following features:

* Program dashboard
* Deadline management
* Registration type management
* Lunch constraints control

Course Materials (AdminMaterials)
---------------------------------

This module provides one view, get_materials.  From this view you can see all of the documents that have been uploaded by teachers for their classes.  You can upload your own files and choose whether they should be associated with an individual class, or if they are for the program as a while.

Uploaded files can also be managed at a lower level using the file browser (/admin/filebrowser/browse).

User morphing capability (AdminMorph)
-------------------------------------

This module provides one view, admin_morph.  You can use the user search to find someone in the system (typically a teacher or student) and then morph into them so you can see the site from that user's perspective.  You will need to click the "Unmorph" link when you are done in order to avoid seeing permissions errors (using the "back" button in your browser will not work).  Morphing into administrators is not permitted as this constitutes a security risk.

Application Review for Admin (AdminReviewApps)
----------------------------------------------

This module is used for programs that have student applications.  Typically teachers do most of the work (creating application questions for their classes, and reviewing the students that apply).  However, this module allows admins to select students to be admitted for the program, seeing the students' applications as well as teacher reviews.

Custom forms and Formstack may be used to augment or replace these features.

Admin Module for showing basic vitals (AdminVitals)
---------------------------------------------------

This module is deprecated and will be removed in a future release.

AJAX Scheduling Module (AJAXSchedulingModule)
---------------------------------------------

This module provides one view, ajax_scheduling.  It is the main interface for assigning times and rooms to classes, using a grid-based interface in your browser.

The scheduling interface will periodically fetch updates from the server so that multiple people can work on scheduling at the same time.  You will be warned if you are trying to create conflicting assignments.  For overriding schedule conflicts and other special cases (like assigning a class to non-contiguous time slots or multiple classrooms), use the manage class page.

The Ajax scheduling module does not have full support for overlapping time slots, and time slots that are not approximately 1 hr long.

Managing Check List Items (CheckListModule)
-------------------------------------------

This module is deprecated and will be removed in a future release.  Please consider using the new "class flags" feature described immediately below.

Class Flags (ClassFlagModule)
-------------------------------------------

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

Communications Panel for Admin (CommModule)
-------------------------------------------

This module allows you to use the Web site to send e-mail to participants in your programs.  You first select the list of recipients and then enter the message title and text.  There are many options for selecting recipients, either a basic list (single criteria) and combination list (multiple criteria combined with Boolean logic).  Be aware that for technical reasons, combination lists often do not contain the set of users you are expecting (this will be addressed in a future release).  Please check that the number of recipients look reasonable before sending an e-mail.  You can use the "recipient checklist" feature to see specific users.

To send an HTML e-mail (e.g. with images and formatting), begin your e-mail text with <html> and end it with </html>.  Besides using proper HTML code in the message text, please test send the message to yourself (before sending to a larger list) so you can verify that the message displays properly.

Credit Card Module (CreditCardModule_Cybersource)
-------------------------------------------------

This is a module to allow credit card payments using the Cybersource hosted order page.  It is used only by MIT.

Credit Card Module (CreditCardModule_FirstData)
-------------------------------------------------

This is a module to allow credit card payments using the First Data hosted order page.  It can be used by LU hosted sites.  It will need to be configured for your specific program, so please contact your mentors and support team to discuss well in advance (at least one month) of your student registration.

Credit Card Viewer(CreditCardViewer_Cybersource)
-------------------------------------------------

This module provides one view, viewpay_cybersource.  The name is a misnomer as it will display accounting information regardless of how that information was collected (Cybersource, First Data, or manual entry).  The view shows a list of students who have invoices for your program, and summarizes their amounts owed and payment[s] so far.  

JSON Data (JSONDataModule)
--------------------------

This module provides a wide variety of information as requested by other program modules, such as the statistics for the dashboard and the Ajax scheduling module.  It should be included with every program.


User List Generator (ListGenModule)
-----------------------------------

This module presents an interface similar to the communications panel, allowing you to specify filtering criteria to get a list of users.  However, instead of sending an e-mail, you are asked which information you would like to retrieve about each user.  This information might include their school, grade level, or emergency contact information.  Lists can be generated in HTML format (for printing) or CSV format (for spreadsheets).

Mailing Label Generation (MailingLabels)
----------------------------------------

If you will be using postal mail advertising for a program, include this module.  It generates HTML pages with the mailing labels for students or schools, so that you can print them out on label sheets.

Nametag Generation (NameTagModule)
----------------------------------

This module is used to generate name tags for students, teachers, and administrators.  For students and teachers, you are presented with the familiar user list filtering options.  For administrators, you will need to enter each person's name and title.  Often the directors will take this opportunity to provide their volunteers with humorous titles.

Be sure to follow the instructions (e.g. no margin, 100% scaling) when printing.  The strange ordering of the output is intentional; after cutting the stack of 8.5" x 11" pieces into 6 piles, these piles can be concatenated to obtain alphabetically ordered name tags.

If you would like to customize the appearance of your name tags, you can create a template override for program/modules/nametagmodule/singleid.html.  The original source is available on Github.

Most Printables for a Program (ProgramPrintables)
-------------------------------------------------

This module provides printable (HTML and PDF) tables for a wide variety of information relating to classes, students, and teachers.  This includes the PDF class catalog, as well as student schedules and room schedules.

Most of our chapters will combine the output of several "printables" to create an admin binder that serves as a reference book during the program.  Contact your mentors or advisors for advice on what information is useful to include.

If you would like to customize the appearance of your student schedules, you can create a template override for program/modules/programprintables/studentschedule.tex.  Be sure to test this with a small subset of students before trying to generate the PDF for everyone.  Generating the schedules can take several minutes.

Resource Management (ResourceModule)
------------------------------------

This module is essential to most programs (e.g. those with classes that need to be scheduled).  The resources page lets you create and modify four types of data for a program:
1) Timeslots - be sure to set these up immediately after creating a program, since they are required for teacher registration to work properly.  You can import timeslots from a previous program that spans the same number of days.  Do not delete timeslots unless you know the consequences.
2) Classrooms - needed for scheduling.
3) Resource types - if you want to give teachers options about what type of classroom/equipment they need (without having to explain in the text boxes) on the class creation/editing form.  You can also modify resource types at /admin/resources/resourcetype.
4) Floating resources - things like LCD projectors and special purpose equipment that will need to be assigned to individual classes and moved from classroom to classroom during the program.

Scheduling checks (SchedulingCheckModule)
-----------------------------------------

During and after scheduling a program, you should periodically visit this page to see if you made any mistakes.  It may take a few minutes to run, but you will see a summary of common issues such as teachers that have to travel between adjacent timeslots and classes that aren't assigned the resources they need.

Old-style scheduling (SchedulingModule)
---------------------------------------

This module is deprecated and will be removed in a future release.  

Survey Management (SurveyManagement)
------------------------------------

Include this module if you are using online surveys.  Surveys must be created at /admin/survey/, but this module will provide links to viewing the results.

Manage Teacher Training and Interviews (TeacherEventsModule)
------------------------------------------------------------

This module should be used if you are having teachers sign up for training and interviews on the Web site.  It lets you define time slots for each of these events and prompts the teachers to select one as part of the registration process.

Volunteer Management (VolunteerManage)
--------------------------------------

Include this module if you will be using the Web site for volunteer registration.  It lets you define time slots for volunteering (each with a desired number of volunteers) and shows you who has signed up for each slot.


== Onsite modules (9) ==

Onsite Reg Core Module (OnsiteCore)

On-Site User Check-In (OnSiteCheckinModule)

Onsite View Purchased Items (OnsitePaidItemsModule)

Show open classes at registration (OnSiteClassList)

On-Site User Check-In (OnSiteCheckinModule)

Onsite Scheduling for students (OnsiteClassSchedule)

Show All Classes at Onsite Registration (OnSiteClassList)

Onsite New Registration (OnSiteRegister)

Automatically Print schedules for Onsite reg (OnsitePrintSchedules)

Volunteer modules (1)
=====================

Volunteer Sign-up Module (VolunteerSignup)

Unsupported/deprecated modules (11)
===================================

SOW Class Reg (StudentClassRegModule)

Module for managing rooms for program (ClassRoomModule)

Credit Card Payment Module (CreditCardModule)

Student Optional Fees (StudentExtraCosts)

Credit Card Payment Module (Cybersource) (CreditCardModule_Cybersource)

Credit Card View Module (Cybersource) (CreditCardViewer_Cybersource)

SATPrep Information (SATPrepModule)

SATprep On-Site User Creation (SATPrepOnSiteRegister)

SATPrep Teacher Information (SATPrepTeacherModule)

SATPrep Interface for Teachers (SATPrepTeacherInput)

SATPrep Schedule Module (SATPrepAdminSchedule)


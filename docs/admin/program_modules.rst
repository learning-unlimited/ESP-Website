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

AdminCore (AdminCore)

Admin Module for showing basic vitals (AdminVitals)

Managing Check List Items (CheckListModule)

Volunteer Management (VolunteerManage)

Application Review for Admin (AdminReviewApps)

Communications Panel for Admin (CommModule)

Most Printables for a Program (ProgramPrintables)

Class Management For Admin (AdminClass)

AJAX Scheduling Module (AJAXSchedulingModule)

Resource Management (ResourceModule)

Survey Management (SurveyManagement)

Course Materials (AdminMaterials)

Application Review for Admin (AdminReviewApps)

Mailing Label Generation (MailingLabels)

User morphing capability (AdminMorph)

Nametag Generation (NameTagModule)

Surveys (SurveyModule)

User List Generator (ListGenModule)

Scheduling (SchedulingModule)

Manage Teacher Training and Interviews (TeacherEventsModule)

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


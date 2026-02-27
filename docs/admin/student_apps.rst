====================
Student Applications
====================

.. contents:: :local:

Note: The website has two different facilities for working with student applications: the older (circa 2007) application questions module, and the newer (circa 2012) student application module. This documentation is about the newer one.

Eventually, this module may support multiple backends for application forms, including custom forms on the website. For now, the only supported backend is Formstack_, a third party form builder. To use, create an application form to your liking using Formstack, then integrate it with the website as described below.

.. _Formstack: http://www.formstack.com/

Deployment Instructions
=======================

Before using this code, a webmaster should have done all of the following:

* Run migrations for the esp.application app
* Install the new program modules (esp.program.modules.models.install)
* Copy media/default_styles/admissions.css to media/styles/

Formstack Form Setup Instructions
=================================

Make an application form using the Formstack form builder. You may add any fields to the form that you want, but you must include (a) a field for ESP username and (b) a dropdown field for each choice slot that asks which class is being applied to.

The username field should be required and read-only. It will be pre-populated by the website when a user is logged in and will be used to link apps with accounts.

The dropdown fields for class choices should include an option for each class in the program. Each option should be associated with its respective class subject (which should be registered on the website in the usual manner) by editing the dropdown field on Formstack, choosing "use separate values", and putting each class's ID number into the "option values" column.

Finally, go to the form settings in Formstack and add a webhook_ to http://WEBSITE_URL/formstack_webhook (where WEBSITE_URL is, for example, esp.mit.edu or stanfordesp.org or splashchicago.learningu.org). This will notify the website whenever the form is submitted, so that the database stays in sync.

.. _webhook: http://blog.formstack.com/2010/create-live-connections-for-your-web-forms-with-webhooks/

Program Setup Instructions
==========================

In order to use Formstack application forms with a program, enable the following modules:

* **Formstack Application Module**: This is the module that embeds a Formstack form on a student-facing page for student applications.
* **Teacher Admissions Dashboard**: Provides an interface for teachers to review applications for their class.
* **Admin Admissions Dashboard**: Provides an interface for admins to review all of the applications in the program.

Now go to /admin/application/formstackappsettings/ and find your program.

1. Fill in your Formstack API key (v1) and hit "save and continue editing"
2. A list of forms connected to your account should appear underneath that box. Find the application form that you created, fill in the form ID number, and hit "save and continue editing"
3. A list of the questions in that form should appear underneath that box. Fill in the field ID numbers for the username field (which is used to link applications with accounts) and the core class fields (which are used to link applications with classes on the website).
4. Put some HTML in the "teacher view template" field; this is a customizable template for what teachers will see when they go to view a student's application. Follow the instructions in the help text for how to include the user's responses in this template.
5. If you are using Formstack for the financial aid form too, do the same for the financial aid form settings.

Student Workflow
================

Visit /learn///studentapp. If you're logged in as an admin, you should see a page (provided that you set things up correctly). Probably, the only thing there is an empty editable text area and a button that says "Continue".

Verify that pressing "Continue" takes you to your application form, and fills in the username field with your username.

Once you've edited the page content to your satisfaction, go back to the formstackappsettings page and check the checkbox at the bottom that says "App is currently open". This will make the "Continue" button visible to all users, and you can now publish the /learn///studentapp link as the link to your application.

Admin Workflow
==============

Visit /manage///admissions as an admin. You should see a dropdown menu at the top, and a big table with lots of columns.

Pick a class. If the class has any applicants, they should appear in the table.

Click on a student's name. It should open up their application in a new window; what exactly shows up here depends on what you used as the "teacher view template" earlier.

Try changing a student's "admin status". The "Save" button should become active, indicating that you have made changes that can be saved. Click to save your changes.

Click "Refresh"; this should cause the table to be repopulated. You should see that your changes are still there.

Click the "(click to add comment)" under admin comment. A dialog should pop up which allows you to type something. Try typing a comment and saving it.

Teachers will only be able to see the applications whose admin status is set to "Approved". Set some applications to "Approved", so that they appear in the teacher view.

Teacher Workflow
================

Visit /teach///admissions as an admin or teacher. This should be a similar UI as the manage page, but with fewer columns in the table, and with a blank pane on the right.

Pick a class. If the class has approved applicants, they should appear in the table.

Click on a student's name. It should open up their application in the right-hand pane.

Try changing a student's "Rating". You should notice that the table sorts itself according to th eratings given, Green > Yellow > Red > None. Otherwise, it should act fairly similar to the /manage/ UI.

Save your changes. If you now go back to the /manage/ UI and view the same applications, you should find that the changes you made are reflected there.

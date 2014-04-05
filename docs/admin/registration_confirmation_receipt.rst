=================================
Registration Confirmation Receipt
=================================

.. contents:: :local:

How Students Confirm Their Program Registration
===============================================

Registration receipts are seen by students in three instances:

* When they click 'Confirm' on the student registration page for the first
  time, they are e-mailed a receipt.

* When they click 'Confirm' on the student registration page, they are
  presented with a printable confirmation receipt in their browser.

* When they click 'Cancel' on the student registration page, they are presented
  with a printable cancellation receipt in their browser.

Creating Registration Receipts
==============================

The HTML confirmation receipt is required and must be created for each program.
If you get server errors when clicking the 'Confirm' button on student
registration, it is likely that the confirmation receipt has not yet been
created.  Follow the directions below to create a receipt.

Text Walkthrough
----------------

From [sitename].learningu.org, log in to your administrator account.
Click 'Administration pages' and then the link for 'Db receipts' in the
'Modules' category.  Take a look at any other receipts that may have been
created as examples.  Click 'Add' and you will be presented with a form to
create a new receipt.

* In the box next to 'Action' type:

  - 'confirm' for the HTML confirmation receipt

  - 'confirmemail' for the plain-text e-mail receipt

  - 'cancel' for the HTML cancellation receipt

* In the dropdown box next to 'Program,' select the program that this receipt
  should apply to.

* In the large text box next to 'Receipt,' enter the contents of the receipt
  template.  Usually the contents of the receipt from a previous program can be
  copied and edited to save time.  This template can include placeholders for
  the students' name, ID, and schedule.  It should also (generally) include the
  following information:

  - How long the students have to change or cancel their registrations.

  - When the program is.

  - Where and when the students should show up for the first activities
    (check-in, first class, etc.).

  - How much money the student will need to bring (if they have financial aid,
    or if they don't).

  - Links and instructions for any forms (liability, waivers, etc.) that the
    students will need to bring.

  - Information about food availability (including the students' reservations,
    if applicable) during the program.

* Click 'Save' and continue to add any other desired receipts.

**Note**: Confirmation e-mails are not sent by default.  You need to turn
them on by checking the 'Send confirmation' box on the appropriate student
registration settings entry accessible from
[sitename].learningu.org/admin/modules/studentclassregmoduleinfo.

Screenshot Walkthrough
----------------------

1. Write the email.

   i. Navigate to [yoursite].learningu.org/admin/.

   #. Click Modules > Db receipts.

      .. figure:: images/registration_confirmation_receipt/fig1.jpg
         :width: 30 %

   #. Click "Add db receipt".

   #. Name the receipt confirmemail (in the "action" field).

      .. figure:: images/registration_confirmation_receipt/fig2.jpg
         :width: 30 %

      .. figure:: images/registration_confirmation_receipt/fig3.jpg
         :width: 30 %

   #. Select the current program from the dropdown menu.

   #. Type your message in the "Receipt" field (use HTML to format).

      .. figure:: images/registration_confirmation_receipt/fig4.jpg
         :width: 30 %

   #. Click "Save".

   #. Your new receipt should appear in the list.

      .. figure:: images/registration_confirmation_receipt/fig5.jpg
         :width: 30 %

#. Enable the confirmation.

   #. Navigate to [yoursite].learningu.org/admin/.

   #. Click Modules > Student class reg module infos.

      .. figure:: images/registration_confirmation_receipt/fig6.jpg
         :width: 30 %

   #. Choose the current program.

      .. figure:: images/registration_confirmation_receipt/fig7.jpg
         :width: 30 %

   #. Scroll to the bottom.

      .. figure:: images/registration_confirmation_receipt/fig8.jpg
         :width: 30 %

   #. Check the "Send confirmation" box and click "Save".


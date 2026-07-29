============================================
 ESP Website Stable Release 15 release notes
============================================

.. contents:: :local:

Changelog
=========

Profiles
~~~~~~~~
- Added a preferred pronouns field to student and teacher profiles (which can be disabled with the ``student_profile_pronoun_field`` and ``teacher_profile_pronoun_field`` tags)

  - These pronouns are shown on various printables (including nametags) and pages across the website (including attendance)
- Now strip any leading or trailing whitespace in user searches
- Added Editable blocks to the alerts on the student profile page
- Fixed a rare bug in the profile form when the ``allow_change_grade_level`` tag was set to True

Accounting
~~~~~~~~~~
- Now require a cost for line items, with the default set to $0.00
- Financial aid approval page now does not approve blank requests by default
- Fixed user search form on accounting pages

Credit Card Payment Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Credit card payments now work with partial financial aid
- Extra cost selections (e.g., lunch, t-shirts) can now be modified after paying

  - If the total cost becomes greater than the previous total, an additional payment can be made
  - This page now has a running tally of the costs and will account for previous payments, program admission fees, and/or financial aid grants
  - We do not handle refunds, so any reduction in total is treated as a donation
  - Supports partial and full financial aid
  - Can be disabled with the ``already_paid_extracosts_allowed`` tag
  - Use this functionality to get lunch orders from your students!

Student Registration
~~~~~~~~~~~~~~~~~~~~
- Fixed the handling of donation line items in the credit card module (hotfixed to SR14)
- Fixed a bug with the credit card form in the credit card module (hotfixed to SR14)
- If there are no costs to cover for a program, the financial aid module is now hidden, even if it is enabled
- If the class changes deadline is still open (i.e., students can make class changes on the normal website), then students can now make class changes on the webapp, even if they aren't checked in

  - The default checkin note at the top of the webapp has been updated to reflect that only classrooms are now hidden until a student is checked in (this text can be modified with a tag)
- Fixed a bug where javascript was being displayed as text in the course catalog
- Added class length, difficulty, and status filters to the course catalog
- Fixed the ability for students to register for classes from the onsitecatalog page

Student self checkin
~~~~~~~~~~~~~~~~~~~~
- Students can now check themselves in (if the tag setting is enabled) if they have completed all required registration steps (e.g., custom forms, payment, etc)

  - If students have not completed any required registration steps, these steps are highlighted on the self checkin page
  - There are two self checkin options: 1) students just need to visit a page and click a button, or 2) students need a code that is unique to them and the program. If using codes, these can be printed on the back of nametags.
  - There is also a tag (enabled by default) to require full payment before allowing self checkin. If a credit card module is enabled, students will be directed there. If no module is enabled, students will be instructed to see an admin team member.

Teacher Registration
~~~~~~~~~~~~~~~~~~~~
- Fixed the "Request Cancellation" button for teachers to cancel classes
- Fixed the formatting of the availability page for various edge cases
- Fixed the "import class" text in teacher registration to be clearer that classes of the current program can be imported (e.g., as a duplicate for different grades)
- Removed an unused view (and the associated permission "Teacher/Classes") that allowed teachers to delete their classes

Custom record types
~~~~~~~~~~~~~~~~~~~
- Admins can now create arbitrary record types which can be bulk set via the User Record Module and can be required for teacher and/or student registration via the relevant tags

AJAX Scheduler
~~~~~~~~~~~~~~
- Added a legend to the AJAX scheduler
- Fixed various bugs related to moderator assignment and scheduling classes with moderators
- Fixed the highlighting of the timeslot headers
- Sections taught by teachers of the selected section are now highlighted
- Fixed classroom tooltips
- Switched to using the ``timeblock_contiguous_tolerance`` tag to define whether timeblocks are contiguous

Themes
~~~~~~
- Added contact info to themes where it was missing
- Now allow more customization of themes; in particular the color/font customization options now actually have effects throughout the theme
- Added a new logo/favicon upload interface on the theme settings page
- Removed the "Clear theme" option to promote the use of built-in themes instead of custom themes
- Fixed a bug that forced admins to hard refresh whenever they changed their website theme
- Added a new theme template loader that will help keep theme templates up-to-date across website releases

  - This does not affect template overrides for theme templates
- index.html pages will now highlight the proper nav bar tab
- Added the ability to modify most of the colors of every theme via the theme editor

Minor new features
~~~~~~~~~~~~~~~~~~
- Added tags for help text for teacher registration fields that did not already have them
- On the tag settings page, tags for help text for fields that are not in use are now hidden
- Added a Captcha field to the contact form to prevent spam
- Added a link to the LU wiki Feature Requests page on the "manage all programs" page
- Removed the time estimate from the comm panel results page and added a link to the email monitoring page
- Added timezones to the manage deadlines page
- Added a user interface to modify the formatting of printable student schedules
- Added the ability to group timeslots into arbitrary custom timeslot groups
- Modules that have been manually enabled will now be copied when using a template program to make a new program

  - All aspects of a template program that are copied to the new program are now listed on the new program form.
- Any/all tag form errors are now shown at the top of the tag settings page
- Added new printables for each line item

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed the receipt form when template overrides exist
- Now skip custom form responses with no responses when loading previous responses
- Removed all tags for custom forms from tag settings page since these should no longer be set manually; custom forms can be assigned to registration modules through the custom form editor
- Categories, record types, and flags that are currently in use can no longer be deleted
- Added documentation to the categories, flag types, and record types page
- Fixed the volunteer CSV download
- Fixed forms so they do browser-side validation before submitting to the server (this was broken in Stable Release 14)
- Class category symbols can only be a single letter now (special characters previously caused issues and will be converted to "Z"s)
- Changed the survey category field to a dropdown menu
- Fixed a bug related to record type names that weren't snake_case
- Fixed an error related to using the bulk account module multiple times with the same prefix
- Fixed a bug related to a missing sibling discount line item
- Fixed various bugs with the module settings user interface
- Fixed the record checking in the student/teacher reg required record interface
- Fixed overflowing scheduling checks
- Removed the ``use_grade_range_exceptions`` option from the Student Class Registration settings form
- Fixed the boolean logic of the line item user search controller filters
- Fixed the Onsite New Student Registration form

January 2024 Patch
===================

Themes
~~~~~~
- Increased the color customizability of the fruitsalad and bigpicture themes (buttons, text, links)
- Fixed edge cases where the dropdown menus on the logo picker page would break
- New logos, headers, and favicons are now loaded immediately when changed
- Added the ability to reset and remove optional fruit salad variables
- Added the ability to reset required fruit salad variables
- Added functionality to prevent the same optional fruit salad variable from being added more than once
- Made the contact info header/footer sections MUCH more customizable in the theme editor

  - The contact info can even be completely blank, that's how customizable it is
- Fixed the caching of the logos on /themes/
- Fixed the styling of /themes/setup
- Changed some of the help text on the theme customization page to be more relevant to the current theme

AJAX Scheduler
~~~~~~~~~~~~~~
- Added the ability to unassign moderators from unscheduled sections in the ajax scheduler
- The selected moderator is now highlighted in the ajax scheduler
- Added a moderator availability scheduling check to the ajax scheduler and the scheduling checks page
- Fixed the moderator title for all checks in the ajax scheduler and the scheduling checks page
- Adjusted the coloration of the cells for the teacher/moderator availability checks to be based on the proportion of teachers that are unavailable as opposed to the raw number
- Fixed errors caused by duplicate room resources when scheduling classes

Minor new features
~~~~~~~~~~~~~~~~~~
- Added a "return to profile" button to the grade change request form
- When approving, cancelling, or rejecting a class, you will now always be redirected to that class's /manageclass page (when deleting a class, you will always go to the /dashboard)
- Improved the download button on the customform response page (made it larger and added a legend)
- Added ability to enable/disable contact form (see the "contact_form_enabled" tag)
- Added a default page at /contact.html (falls back to QSD if it existed before)
- Added simple validation for JSON-formatted tags
- Empty categories in the catalog are now hidden (including when catalog filters are used)

  - This can be disabled by unchecking the "hide_empty_categories" tag

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed the lists of permissions in the custom form builder
- Fixed the loading of previously set permissions in the custom form builder
- Fixed edge cases when submitting the volunteer or class registration forms
- Fixed the moderator titles throughout the dashboard
- Fixed the formatting of blank nametags
- Fixed receipt template loading
- Fixed a bug that allowed teachers to access open class registration even when it was disabled
- Fixed the caching of the open class registration setting
- Fixed a very rare bug caused by using the autoscheduler when open class registration was disabled
- Fixed the /faq.html page to now show all theme-related bits
- Fixed a bug that caused links in the admin toolbar to not update when a program name was changed
- Fixed the categories and flags links on the program settings page
- Fixed an oversight where some student modules did not check the grade level of a student
- Fixed the rapid checkin page

March 2024 Patch
================
Due to changes in how Gmail and other email clients are now handling certain kinds of emails, we have made the following changes:

- Emails from the Comm Panel can now only be sent from email addresses ending in @learningu.org or @subdomain.learningu.org (e.g., @yale.learningu.org)
  
  - If you have a custom domain that should work too (e.g., stanfordesp.org)
  - Each site now has a "info@yoursitehere" redirect that should redirect to your chapter's email address (e.g., info@yale.learningu.org now redirects to yalesplash@gmail.com) and will be used by default in the Comm Panel
  - As always, you can put whatever you want in the "Reply-to" field
- All Comm Panel emails will now be sent with a customized one-click unsubscribe link that email clients can now show to the recipients

  - Clicking on this link will instantly deactivate their account (effectively unsubscribing them from emails)
- If you would like to include a similar unsubscribe link in the text of your emails, you can use the `{{ }}` dropdown menu

  - This unsubscribe link will take recipients to a page where they will need to confirm that they would like to deactivate their account and unsubscribe from emails

Minor bug fixes
~~~~~~~~~~~~~~~
- Program links now work after changing a program's name
- The "Signup" button text color is fixed on the fruitsalad theme

============================================
 ESP Website Stable Release 15 release notes
============================================

.. contents:: :local:

Changelog
=========

Profiles
~~~~~~~~
- Added a preferred pronouns field to student and teacher profiles (which can disabled with the `student_profile_pronoun_field` and `teacher_profile_pronoun_field` tags)
  - These pronouns are shown on various printables (including nametags) and pages across the website (including attendance)
- Now strip any leading or trailing whitespace in user searches
- Added QSD blocks to the alerts on the student profile page
- Fixed a rare bug in the profile form when the `allow_change_grade_level` tag was set to True

Accounting
~~~~~~~~~~
- Now require a cost for line items, with the default set to 0.00
- Financial aid approval page now does not approve blank requests by default
- Fixed user search form on accounting pages
- Credit card payments now work with partial financial aid
- Fixed the handling of donation line items in the credit card module (hotfixed to SR14)
- Fixed a bug with the credit card form in the credit card module (hotfixed to SR14)
- Extra cost selections (e.g., lunch, t-shirts) can now be modified after paying

  - If the total cost becomes greater than the previous total, an additional payment can be made
  - We do not handle refunds, so any reduction in total is treated as a donation
  - Supports partial and full financial aid
  - Can be disabled with the `already_paid_extracosts_allowed` tag

Custom record types
~~~~~~~~~~~~~~~~~~~
- Admins can now create arbitrary record types which can be bulk set via the User Record Module and can be required for teacher and/or student registration via the relevant tags (see above)

Student self checkin
~~~~~~~~~~~~~~~~~~~~
- Students can now check themselves in (if the tag setting is enabled) if they have completed all required registration steps (e.g., custom forms, payment, etc)
- If students have not completed any required registration steps, these steps are highlighted on the self checkin page
- There are two self checkin options: 1) students just need to visit a page and click a button, or 2) students need a code that is unique to them and the program. If using codes, these can be printed on the back of nametags.
- There is also a tag (enabled by default) to require full payment before allowing self checkin. If a credit card module is enabled, students will be directed there. If no module is enabled, students will be instructed to see an admin team member.

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

Minor new features
~~~~~~~~~~~~~~~~~~
- Added tags for help text for teacher registration fields that did not already have them
- On the tag settings page, tags for help text for fields that are not in use are now hidden
- Added a Captcha field to the contact form to prevent spam
- Added a link to the LU wiki Feature Requests page on the "manage all programs" page
- Removed the time estimate from the comm panel results page and added a link to the email monitoring page
- Added timezones to the manage deadlines page
- Added a user interface to modify the formatting of printable student schedules
- Added class length, difficulty, and status filters to the course catalog
- Added the ability to group timeslots into arbitrary custom timeslot groups
- If the class changes deadline is still open (i.e., students can make class changes on the normal website), then students can now make class changes on the webapp, even if they aren't checked in. The default checkin note at the top of the webapp has been updated to reflect that only classrooms are now hidden until a student is checked in (this text can be modified with a tag).
- Modules that have been manually enabled will now be copied when using a template program to make a new program. All aspects of a template program that are copied to the new program are now listed on the new program form.
- If there are no costs to cover for a program, the financial aid module is now hidden, even if it is enabled

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed the receipt form when template overrides exist
- Fixed the request cancellation button for teachers to cancel classes
- Now skip custom form responses with no responses when loading previous responses
- Removed all tags for custom forms from tag settings page since these should no longer be set manually; custom forms can be assigned to registration modules through the custom form editor
- Categories, record types, and flags that are currently in use can no longer be deleted
- Added documentation to the categories, flag types, and record types page
- Fixed the Onsite New Student Registration form
- Fixed the volunteer CSV download
- Fixed forms so they do browser-side validation before submitting to the server (this was broken in Stable Release 14)
- Class category symbols can only be a single letter now (special characters previously caused issues and will be converted to "Z"s)
- Fixed the onsite catalog
- Changed the survey category field to a dropdown menu
- Fixed a bug related to record type names that weren't snake_case
- Fixed an error related to using the bulk account module multiple times with the same prefix
- Fixed a bug related to a missing sibling discount line item
- Fixed the formatting of the availability page for various edge cases
- Fixed various bugs with the module settings user interface
- Fixed a bug where javascript was being displayed as text in the course catalog

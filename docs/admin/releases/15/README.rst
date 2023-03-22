============================================
 ESP Website Stable Release 15 release notes
============================================

.. contents:: :local:

Changelog
=========

Custom record types
~~~~~~~~~~~~~~~~~~~
- Admins can now create arbitrary record types which can be bulk set via the User Record Module and can be required for teacher and/or student registration via the relevant tags (see above)

Student self checkin
~~~~~~~~~~~~~~~~~~~~
- Students can now check themselves in (if the tag setting is enabled) if they have completed all required registration steps (e.g., custom forms, payment, etc)
- If students have not completed any required registration steps, these steps are highlighted on the self checkin page
- There are two self checkin options: 1) students just need to visit a page and click a button, or 2) students need a code that is unique to them and the program. If using codes, these can be printed on the back of nametags.

Themes
~~~~~~
- Added contact info to themes where it was missing
- Now allow more customization of themes; in particular the color/font customization options now actually have effects throughout the theme
- Added a new logo/favicon upload interface on the theme settings page


Minor new features
~~~~~~~~~~~~~~~~~~
- Added tags for help text for teacher registration fields that did not already have them
- On the tag settings page, tags for help text for fields that are not in use are now hidden
- Added QSD blocks to the alerts on the student profile page
- Financial aid approval page now does not approve blank requests by default
- Added a Captcha field to the contact form to prevent spam

Minor bug fixes
~~~~~~~~~~~~~~~
- Now require a cost for line items, with the default set to 0.00
- Fixed the receipt form when template overrides exist
- Fixed the request cancellation button for teachers to cancel classes
- Now skip custom form responses with no responses when loading previous responses
- Removed all tags for custom forms from tag settings page since these should no longer be set manually; custom forms can be assigned to registration modules through the custom form editor
- Categories, record types, and flags that are currently in use can no longer be deleted
- Added documentation to the categories, flag types, and record types page
- Fixed user search form on accounting pages
- Credit card payments now work with partial financial aid
- Fixed the handling of donation line items in the credit card module (hotfixed to SR14)
- Fixed a bug with the credit card form in the credit card module (hotfixed to SR14)
- Fixed a bug that forced admins to hard refresh whenever they changed their website theme
- Fixed the Onsite New Student Registration form
- Now strip any leading or trailing whitespace in user searches
- Fixed the volunteer CSV download
- Fixed forms so they do browser-side validation before submitting to the server (this was broken in Stable Release 14)
- Class category symbols can only be a single letter now (special characters previously caused issues and will be converted to "Z"s)
- Fixed the onsite catalog

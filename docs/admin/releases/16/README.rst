============================================
 ESP Website Stable Release 16 release notes
============================================

.. contents:: :local:

Changelog
=========

Themes
~~~~~~
- Removed some unused variables
- Renamed some variables for clarity
- Made button types have consistently editable colors across themes
- Made the theme editor more theme-specific by removing irrelevant variables and adding some help text
- Fixed the "Reset Color" buttons on the theme customization page for optional variables and non-theme-specific variables
- Fixed the theme customization page so that only optional variables have a "Remove Variable" button
- Fixed the alignment and sizing of the logo in the fruitsalad theme
- Added the ability to reorder nav structure and contact links

  - This section of the theme setup page also now has a less cluttered and more user friendly interface
- Added a link to the privacy policy to the left header in the bigpicture theme

Scheduler
~~~~~~~~~
- Fixed the highlighting of the moderator directory cell
- Moderators are now highlighted when they are selected via the info panel for a section
- The scheduler now waits until all changelog items are applied before allowing the user to interact with it
- Classes that are cancelled and unscheduled outside of the scheduler are now immediately removed from the scheduler

Student registration
~~~~~~~~~~~~~~~~~~~~
- Removed duplicate and unneeded summary lines in the extracosts form for certain setups
- Fixed saving preferences in the two-phase class lottery

Program settings
~~~~~~~~~~~~~~~~
- Added help text to the color_code class registration module info field

  - The widget for this field is now a color picker with regex validation to ensure values are hex color codes
  - Any old values for this field have been updated to this new format
- Made the registration receipt prettier and more informative

  - This receipt is shown to students after clicking the "confirm registration" button
  - The receipt page is now themed (used to be just a white page) and now has a button to print the receipt and a button to return to the main registration page
  - The receipt now includes program information (date range and registration close date), payment information (including amount owed and optional purchases), and a pretty class schedule
  - The "pretext" can be edited by changing the confirm receipt on the settings page
  - The entire receipt can be overriden by a single template override or by program-specific template overrides (like before)
- Made the registration confirmation email prettier and more informative (same changes as the registration receipt described above)

  - Because this receipt now includes a schedule, clicking the confirmation button always sends a new copy of the confirmation email
- Now prevent programs with duplicates names and or URLs
- When a program name is changed, the account name for that program is similarly changed
- Errors in the new program and program settings forms are now shown as form errors instead of as a Whoops page
- Fixed widths of the URL and email redirect tables
- The Line Items module is now included when charging for extra items

Onsite
~~~~~~
- Made the rapid check-in messages more obvious
- Fixed attendance barcode scanning
- Fixed the timeslot dropdown menu in the admin attendance module

Communications panel
~~~~~~~~~~~~~~~~~~~~
- Named "mailboxes" are now allowed in the comm panel (e.g., "Will's Server <info@test.learningu.org>")
- The default grade limits are now only enforced in the communications panel and not in other user search controller modules (e.g., user list generator)
- Fixed dynamic behavior of the user type field and filters

  - When changing the user type, all filters are now cleared
- Fixed the "Teachers of a student" filter

Minor new features
~~~~~~~~~~~~~~~~~~
- Added a button to scroll to the top of the catalog
- Programs for which users have registered but have not occurred are now included in the the post-profile list of programs
- Cleaned up the UI for checking for duplicate emails during account creation

  - Emails are now only considered duplicates if users want to make accounts of the same type
  - For privacy reasons, first and last names are no longer shown
  - **Checking for duplicate emails is now the default behavior** (this can be disabled using the "ask_about_duplicate_accounts" global management tag)
- The financial aid approval module now includes financial grant information for approved requests
- Financial aid requests are now less cramped in the financial aid approval module, with the extra financial information now hidden by default
- Made the usersearch warning/messages prettier
- Linked model fields can no longer be added to existing custom forms
- After emails are sent, the individual message texts are now deleted to save database storage size

  - We've also deleted all of these message texts for previously sent emails
  - Note that the original, non-user specific texts and the individual user-level records for sent emails still remain in the database

Minor bug fixes
~~~~~~~~~~~~~~~
- Removed the mailing labels module
- Fixed the profile form when numbers are used for school names
- Existing accounting transfers are now updated when the program admission cost is changed
- Removed links to nonexistent DVI and PS catalogs on the printables page
- Removed outdated "Guide for happy printables" from the printables page
- Unmorph button now properly hides after unmorphing
- Fixed the status field in the class management form
- Fixed the regex restriction for the director email field
- Fixed the date format in the volunteer request form help text
- The "Open" deadlines button now properly opens deadlines that are currently set to open in the future
- Now display a 404 page when user attempts to download a file that doesn't exist
- Fixed the volunteer form for very small user ID numbers
- Fixed the selectList_old page
- Fixed the links in the class registration email that is sent to admins

Development changes
===================

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded Python (2.7 -> 3.7)
- Upgraded flake8 (2.5.0 -> 3.9.2)
- Upgraded ipython (3.2.1 -> 7.34.0)
- Upgraded pillow (6.2.2 -> 8.3.2)
- Upgraded pydns (2.3.6 -> 3.2.1)
- Upgraded Pygments (2.0.2 -> 2.10.0)
- Upgraded stripe (1.19.1 -> 2.60.0)
- Upgraded twilio (3.6.5 -> 6.63.2)
- Upgraded xlwt (1.0.0 -> 1.3.0)
- Removed django-selenium
- Added dill
- Added setuptools
- Added wheel

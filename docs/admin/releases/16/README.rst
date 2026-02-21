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
  - The entire receipt can be overridden by a single template override or by program-specific template overrides (like before)
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

June 2025 Patch
===============

New theme!
~~~~~~~~~~
For the first time in 9 years, we are adding a new theme to our roster! We are including a beta version of this theme, called "droplets", in this patch release and plan to release a final version in another patch later this summer after we collect and address feedback. The key foci for this new theme are: a modern "feel", responsiveness and mobile friendly, flexible and customizable, dropdown menus to accommodate complex navigation, and better use of screen width.

Notables features of the new theme include the following:

- A clean header navigation bar and matching footer
- Hoverable dropdown menus for navigation (customizable as with other themes)

  - This includes the hidden admin toolbar
- Built with `Bootstrap <https://getbootstrap.com/>`_ to have a modern "feel"

  - We're still using an old version of Bootstrap, but we plan to upgrade that in the future
- Designed from the ground up to be mobile friendly

  - Some individual pages may still not be entirely mobile friendly, but we're hoping to fix that in the future
  - We're hoping to expand this to other themes in the future
- Wider content (the main content is up to 66% wider than on bigpicture and 95% wider than on fruitsalad!)
- Taller content (we've reduced the size of the header)
- Customization

  - Font size
  - Header/footer colors
  - Dropdown menu color
  - Logo and header visibility
  - Navigation and contact info

As part of the release of this new theme, we have also implemented the following theme-agnostic features:

- Partial redesign of the Main Program Management page
- Partial redesign of the Main Onsite page
- Partial redesign of the Dashboard page
- Complete redesign of the Printables page
- Expansion of various forms and tables to use more screen width
- Partial redesign of the theme editor

Minor new features
~~~~~~~~~~~~~~~~~~
- Added a default email template which can be overridden with a template override of 'email/default_email.html'

  - We plan to expand on this functionality in the future with a selection of templates and the ability to easily make your own
- Cleaned up the styling of several printables (e.g., rosters and attendance lists)
- Added a small hover effect to the left-side tabs in the fruitsalad theme
- Added a `robots.txt <https://en.wikipedia.org/wiki/Robots.txt>`_ file to prevent various AI bot crawlers from accessing the website
- Replaced the very specific "Planned Purchases" help text in the class registration form with much more generic help text (which can still be changed using the 'teacherreg_help_text_purchase_requests' tag)
- Improved the error messages when trying to access a custom form module during student/teacher registration that isn't properly configured
- The admin toolbar is now visible even when morphed

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed rendering of the bottom of the class catalog page
- Fixed an error associated with the Student Profile Form when the 'show_student_graduation_years_not_grades' tag was enabled
- Fixed a loophole where unauthorized users could edit the web page for a class
- Fixed the handling of school names in /manage/statistics
- Fixed the handling of teacher biography photos in Python 3
- Fixed the display and saving of navigation icons in the theme editor (for bigpicture and droplets only)
- Fixed operationality of various buttons in the lottery frontend module
- Fixed the class lottery to run in Python 3
- Fixed the size of the "Sign Up" text in the fruitsalad theme
- Fixed the Teacher Events Management Module erroneously appearing in the "Additional Modules" list when it already appears above
- Fixed a bug that occurred when a student opted to make a donation, then paid via credit card, then revisited the extra costs page (these donations are now shown on the extra costs page to reduce confusion)
- Fixed a bug that occurred when the QSD field on the /myesp/accountmanage/ page was edited (this editable field has now been moved beneath the important buttons on this page)
- Fixed the generation of the meal tickets printable
- Fixed various bugs in the UserSearchController (the UI that is used for the comm panel), mostly related to when a user is directed here with a custom link
- Fixed the functionality of the unenroll module and made some UI improvements (this module hadn't been touched in 9 years)

October 2025 Patch
==================

Minor new features
~~~~~~~~~~~~~~~~~~
- Added the ability to set a tag with a Google Analytics ID ("google_analytics_id") that enables Google Analytics monitoring for nearly all pages of the site
- Added the droplets theme to the theme documentation
- Added the option to change the width at which the droplets theme converts from desktop mode to mobile mode
- Added a button in the ajax scheduler to clear the scheduling cache
- Made the bigpicture theme much more mobile friendly (includes dynamic page width and a separate navigation menu for mobile)
- Email previews are now rendered in iframe elements to isolate any stylings that would otherwise alter the main web page
- Updated the default favicon to have a transparent background
- Added a backup of the default favicon so it is always available as an option on the logo picker page
- Converted the class category and flag type menus to checkboxes in the program settings page
- Added an option to include an editable textbox to the footer in all themes
- Padding at the top and bottom of the page is now calculated dynamically based on the heights of the header and footer
- Improved the error shown when the credit card module is not set up properly
- Class web pages (generally made by teachers) now only support Markdown (the HTML editor has been replaced with a Markdown editor and all old web pages have been cleaned to only have Markdown)
- Redesigned the survey management landing page

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed various bugs related to custom forms
- Fixed the creation of teacher interview events
- Restored the link to the Statistics page from the Manage All Programs page
- Fixed the behavior when attempting to permanently delete user objects
- Fixed the formatting of the volunteer CSV download
- Fixed the overflow of text and popups in tables on the dashboard and on the main teacher registration page
- Fixed the handling of templates in the communications panel
- Fixed the sequence of the credit card and confirm registration modules
- Fixed the handling of the teacher text button on the teacher checkin page when texting is not enabled
- Fixed the text on the communications panel after using the recipient checklist
- Fixed the width of buttons for the droplets theme

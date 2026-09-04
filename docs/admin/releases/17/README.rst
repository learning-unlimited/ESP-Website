============================================
 ESP Website Stable Release 17 release notes
============================================

.. contents:: :local:

Changelog
=========

Themes
~~~~~~
- **Upgraded Bootstrap from 2.3.2 to 5.3.3**, in staged phases (2 → 3 → 4 → 5)

  - Bootstrap is now installed as an npm dependency instead of being committed
    into the repository, so future upgrades are much simpler
  - The theme build pipeline moved from LESS to SCSS; the legacy LESS pipeline
    has been removed entirely
  - Glyphicons have been replaced by Bootstrap Icons
- **Added support for Bootswatch themes**

  - Admins can now pick a Bootswatch theme in the theme editor to use as the
    *base* look for their site, and the existing color customizer then layers
    on top of it
  - Every field in the customizer (scaffolding, links, typography, buttons, and
    each theme's navbar, sidebar, and tab colors) is derived from the selected
    Bootswatch palette, with contrast-aware values computed for colors that
    have no direct Bootswatch equivalent
  - Only variables that are actually changed are applied as overrides, so the
    rest of the page continues to follow the Bootswatch theme
  - The vapor, superhero, and quartz Bootswatch themes are excluded
  - Legibility fixes were made to droplets, bigpicture, and fruitsalad so they
    read correctly on dark Bootswatch themes
- Added configurable admin toolbar links, managed through theme settings
- Added modern favicon files and listed them in the page ``<head>``

  - All favicon variants are now generated automatically when a new favicon is
    selected
  - Favicons are now sorted by date on the logo picker page
- Added OpenGraph and Twitter meta tags so links to the site preview correctly
  when shared
- Added a card-like layout and better spacing to the landing page, and improved
  the spacing between the navigation and the homepage content
- The login box is now rendered server-side rather than shown and hidden by
  JavaScript, which removes the flash of unstyled content on page load and the
  duplicate login forms that could appear
- Login and logout buttons now use standard Bootstrap colors, and the login
  input spacing in the navigation bar has been fixed
- Highcharts is now loaded from ``cdn.learningu.org`` instead of a third-party CDN
- Made the ``tabcolor0`` base color darker in fruitsalad
- Removed the unused vendored copies of YUI and jsTree
- Fixed the theme editor crashing when ``images/theme`` contains a subdirectory
- Fixed the theme customization page crashing for the droplets theme
- Fixed a syntax error when the theme navigation JSON is empty
- Fixed the theme recompilation settings
- Fixed the rendering of the fruitsalad front page bubbles, and the tab colors
  used when URLs match identically or partially
- Fixed a JavaScript error in fruitsalad when the target element is missing
- Fixed the theme editor markup for the circles theme, and the HTML of theme
  buttons

Program management dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **Redesigned the program management dashboard**

  - The vertical setup-steps table is now a horizontal, Gantt-style timeline
  - Module categories are collapsible
  - Module link captions are now hover tooltips instead of inline text, giving
    a much cleaner button grid
- **Added a search box for management pages.** Modules opt in with search
  keywords, so searching for e.g. "nametags" or "check-in" jumps straight to
  the right page
- Promoted many more management buttons into featured categories, reorganized
  the categories to match the search categories, added a Financial and
  Accounting category, and hid categories that are empty
- Added a banner that appears when a program has non-default tags configured,
  so admins are not caught out by inherited settings
- Reordered the elements on the Manage Programs page and added headers
- ``/myesp`` now redirects to the account management page
- Removed the redundant AdminMorph module
- Fixed the accepted-student count on the dashboard, which is now hidden when
  applications are not in use and excludes expired registrations
- Fixed priority counts so they include all priority levels, on the dashboard
  and in the related modules
- Fixed the overflow of the Email Status button and the left alignment of the
  admin toolbar

Module management
~~~~~~~~~~~~~~~~~
- **Rebuilt module management around an interactive timeline grid.** Instead of
  a flat sortable list with deadlines edited elsewhere, modules are laid out
  against the program's dates:

  - Modules can be reordered by dragging, and the required flag, required
    label, and link title can be edited inline
  - A side drawer is used to add modules, with settings pulled in dynamically
  - Modules whose order or required status is enforced by the backend are
    locked, so a change that would be silently undone on save is prevented up
    front; conflict detection warns about overlapping windows
  - Module permissions are now synchronized automatically from the timeline
    dates
  - You are asked to confirm changes that would affect students who are
    actively registering
  - The whole interface is keyboard navigable
- Each module now carries its own start and end dates, and modules are filtered
  by time for non-admin users
- New programs are now created with sensible initial module permissions and dates
- **Permissions can now be scoped to a user filter**, so a permission can be
  granted to just the users matching a saved user search rather than to a whole
  user role
- Module link titles can now be edited per program
- Added a registration checklist to required module pages, so students and
  teachers can see where they are in the process from anywhere in registration
- Added date range validation to the deadline and registration forms
- Module defaults defined in code are now always applied, so code changes are
  no longer masked by stale database rows
- Added CSRF protection to the module management forms
- Fixed the program modules form field, and the module name shown in form errors

Program settings
~~~~~~~~~~~~~~~~
- Added validation for the program maximum size and grade range, and rejected
  invalid or negative grade ranges in the Django admin
- Admin fields that break the site when changed can no longer be edited
- Default email list entries are now created automatically for new sites
- Added a "Load default template" button to the template override admin form
- Added help text to many model fields, which improves the built-in admin
  documentation
- The author of an object is now set automatically in the Django admin
- Destination email addresses for plain redirects are now validated
- Programs can now be deleted by an admin without manually cleaning up
  resources first
- Added a compulsory timeslot checkbox to the resources page
- Available floating resources are now filtered by their "returned" status
- Added a scheduling check that detects unsatisfiable moderator movement
  dependency loops
- **Teacher event types are now configurable** rather than hard-coded, so
  admins choose which event types appear in teacher signup and in the teacher
  events management page
- Fixed the admin UI overflowing when a Tag value is very long
- Fixed the template override diff behavior

Scheduler
~~~~~~~~~
- **Added support for recurring classes** — a section can now be scheduled into
  several separate occurrences rather than one contiguous block

  - Recurring controls appear in the scheduler and in the section info panel,
    with a corresponding legend entry
  - Classes longer than a single time block are handled correctly
  - Recurring meetings are shown in student schedules, the onsite schedule
    view, and teacher registration displays
  - A program tag makes printed student schedules include one row per occurrence
- Scheduler messages are now shown as toast notifications instead of a text log
- Refactored the scheduler tooltips to use event delegation
- Moved the Clear Change Log button so it is reachable when the loading overlay
  is showing, and relocated it on the page
- The teacher class registration form now calculates and shows how many
  sections are possible for a given class length
- Made it easier to print schedules from the class changes grid
- Fixed changelog fetching bugs that could cause scheduled classes to disappear
  from the scheduler
- Fixed the cache dependencies for section teacher availability
- Fixed a swap constraint delegation bug in the autoscheduler
- Fixed sortable tables not re-sorting when their data is updated after sorting
- Fixed the ordering of timeblocks on the class changes page, which are now
  chronological
- Fixed the handling of parallel lunch sections, and replaced hard-coded
  "Lunch" category checks with a proper category flag
- Fixed the class duration dropdown silently disappearing when no timeslots are
  configured; a warning is now shown instead

Catalog
~~~~~~~
- **Added the option to split the catalog into separate pages by category**,
  controlled by a program tag. Students see a category list and drill into one
  category at a time, instead of one very long page
- Added difficulty descriptions to the catalog, so the numeric difficulty
  rating is explained in words
- The catalog now respects the Student/Catalog deadline, so it can be opened and
  closed independently of the rest of student registration
- Past enrolled classes are now hidden
- Fixed the sorting of the catalog, which now orders classes by their earliest
  section time
- Fixed unicode handling in PDF catalog generation
- Fixed the caching dependencies for the cached catalog
- Fixed the appearance of an empty "Classes Already Registered" section

Student registration
~~~~~~~~~~~~~~~~~~~~
- **Registering for a class that conflicts with an existing class now offers to
  replace the conflicting class(es)** after an explicit confirmation, in both
  the main catalog and the onsite web app, instead of simply refusing
- Added a "Cancel all for this day" button to the student schedule
- **Students with approved financial aid can now cancel their registration**,
  which was previously blocked, with appropriate messaging about refunds
- **"Phase Zero" and "Student Lottery" are now consistently called "Program
  Lottery"** in all user-facing text
- Two-phase registration can now require a minimum number of classes, using the
  "twophase_min_classes" tag
- Lottery utility is now scaled by class duration
- **Students can opt out of having a paper schedule printed for them**, using a
  checkbox on the student registration main page
- The credit card statement warning is now an inline banner above the pay
  button, shown only when there is an outstanding balance, rather than a modal
  that pops up on page load
- The Credit Card module can now be made **required only when a student owes at
  least $0.50**, using the "creditcard_required_if_amount_due" tag
- The program registration notice is no longer shown to parent accounts
- Fixed race conditions in class registration and section preregistration that
  could result in over-enrollment; registration operations are now wrapped in
  database transactions
- Fixed the extra costs form showing a NaN total when a quantity was left empty,
  and its handling of non-numeric custom amounts
- Simplified the handling of extra costs in the accounting controller
- Fixed the upcoming-timeslot pre-check in the unenroll module
- Fixed Mailman lists not updating when a student unenrolls from all of their
  classes
- Fixed duplicate error messages and unclear required-field indication on the
  "how did you hear about us" field
- Fixed corrupted class change emails
- Fixed the waitlist subscription record not being created correctly
- Fixed overly restrictive permission checks on the registration redirect
- Fixed the registration-closed filter for non-onsite users when filling a slot
- Fixed a database error when a lottery record was created without a program
- Student applications: empty application questions are no longer created on a
  partial submit, the responses shown for the second and third class choices
  are now correct, the application review page no longer errors for students
  with no application, and the Django admin page for adding a student
  application works again

Teacher registration
~~~~~~~~~~~~~~~~~~~~
- **Teacher event signup now uses an interactive calendar** instead of a flat
  list of times
- Previously uploaded documents are now offered as suggestions on the class
  documents and teacher bio pages
- Teachers can now remove their profile picture from the bio edit page
- Class section cancellation reasons are now saved when a class is cancelled
- Coteacher availability errors are now more informative
- Made volunteer registration visually distinct from teacher registration, so
  it is obvious which form you are on
- Fixed the teacher bio module being marked incomplete when the optional short
  bio was left empty
- Fixed the class size dropdown appearing blank, and the resulting form errors,
  when an admin had set a maximum class size outside the standard options
- Fixed the tampering risk in the coteacher form submission
- Fixed old teacher bio URLs, which now redirect correctly
- Fixed the class copy and moderator list rows, which were missing user context
- Fixed several views that read parameters from the wrong place on GET versus POST

Onsite
~~~~~~
- **Improved rapid check-in**: search by first name, filter the results, and
  clearer barcode visibility
- Barcode check-in now handles records and payment, and no longer errors on
  non-numeric user IDs
- **Teachers who checked in on a previous program day but not yet today are now
  badged on the missing teachers page**, so admins know who probably just needs
  a reminder
- **Rebuilt the publicly viewable open class list**: a proper themed table with
  timeslot group headers, an empty-state message, and a timeslot filter
  dropdown that defaults to the current timeslot

  - The page no longer force-refreshes on a blind timer; it now reloads at the
    end of a scroll cycle, so the list is not interrupted mid-scroll
- Added a class search box to the student onsite catalog page
- The onsite "schedule students" user search now uses AJAX autocomplete
- **Added an Undo button for accidentally marked student attendance**, which
  also reverses the automatic program check-in it created
- Added a schedule PDF download button to the onsite check-in interface
- Replaced the table-based navigation bar in the student onsite web app with
  semantic markup and flexbox
- Fixed accounts created in bulk missing the profile data needed for onsite use
- Fixed a crash in the onsite check-in undo handlers, an infinite loop in onsite
  attendance, and a race condition in attendance sorting
- Fixed the walk-in sanitization only processing the first section
- Fixed a missing authorization check in the student attendance AJAX endpoint
- Check-in database operations are now wrapped in transactions
- Fixed the teacher check-in page erroring on non-numeric input, the shortcuts
  box on the missing teachers page, and the default view of that page
- Fixed the class capacity used by the open class list

Printables
~~~~~~~~~~
- **Large batches of student schedules are now generated asynchronously**, with
  a job status page, so printing hundreds of schedules no longer blocks or times
  out
- Added an option to expire old print requests when opening the print schedules
  page
- Teacher schedules and nametags can now be sorted by first class
- Nametags now use the chapter's theme logo instead of a placeholder image
- The nametag title is autofilled with the group name when "Other group" is
  selected
- Added a compact check-in view to the teacher list printables
- Fixed the column widths of the "Rooms by Time" printable
- Fixed stray characters in LaTeX output, and a LaTeX crash when ``\LaTeX`` was
  used in math mode
- CSV downloads now have the correct MIME type and filename header, and several
  CSV export crashes have been fixed
- ``poll_schedules.sh`` now accepts a program as a command line argument and
  correctly detects a failed login

Class flags
~~~~~~~~~~~
- **Flag types can now be marked visible to teachers**, and can optionally email
  all of a class's teachers when such a flag is added. Visible flags appear on
  the teacher class list and class status pages
- **Flags can now be resolved rather than deleted**, keeping the record in the
  system along with who resolved it and when. Class search gained a filter for
  resolved status
- **Added an engine for automatically adding flags.** Admins define query-based
  rules from the class search page, optionally with a comment and teacher
  notification, and matching classes are flagged as they are created. A rule can
  also be applied to all existing matching classes when it is created
- Flag audit trails are now preserved when a user account is deleted
- Added tab order to the flag creation and editing form fields
- Fixed cross-program access to flags, the response format of the flag edit
  endpoint, and error handling when a new flag notification email fails

Surveys
~~~~~~~
- **Survey questions can now be exported to and imported from CSV**, with a
  downloadable template, validation, and a preview screen before the import is
  committed
- **Teachers can now see all of their student survey feedback from every program
  they have taught on a single page**, instead of clicking through each program
- Redesigned the favorite classes survey pages
- Improved the survey results UI: buttons are greyed out when there are no
  surveys, tooltips were added, and the favorite classes page now explains
  itself when there are no results
- Fixed histogram rendering and the handling of long answer questions
- Fixed the favorite classes results erroring when a survey has no "overall
  rating" question
- Fixed survey answer values that were corrupted by the Python 2 to 3 migration

Communications panel
~~~~~~~~~~~~~~~~~~~~
- **Added an email preview**: render an email with sample user data before
  sending, and send a test copy to yourself
- **A warning is now shown when an email links to a different program**, which is
  a common copy-and-paste mistake
- Added safety warnings to the mass mailer, and removed the artificial delay
  between sends
- Recipients drawn from a class or section list are now de-duplicated, so nobody
  receives the same email twice
- Added ``program.date``, ``program.date_range``, and
  ``program.teacher_reg_deadline`` as available variables
- Fixed images inserted into emails using relative URLs, which broke them in
  mail clients
- Fixed combination queries generating an incorrect filter
- Fixed the grade filter warning always being shown
- Fixed the mail gateway relay: handler dispatch and bounce notifications
- Fixed the confusing SendGrid link shown in the password reset email
- Fixed a crash when generating email data for a program with no sent emails,
  and a stale email address cache when fetching a program's teachers
- Fixed crashes in the group text and user group modules when a saved filter was
  missing or invalid, or when a user had no contact information
- The text messaging script now uses standard command line argument parsing

Accounting and payments
~~~~~~~~~~~~~~~~~~~~~~~
- **Added an admin page for issuing Stripe refunds.** Search for a student, see
  each transaction's original amount, the amount already refunded, and the
  amount still refundable, and submit a partial or full refund that is processed
  through Stripe immediately

  - A confirmation screen reports success or failure, and the CFO is emailed in
    either case
  - The page is linked under Quick Links on the management dashboard
- **Refunds now generate proper accounting entries**, are tracked per user, and
  are taken into account when calculating the amount due; they appear in the
  accounting summary and on transaction records
- Reworked the credit card revenue summary with time-based fetching and
  per-program isolation
- **Added donation and admission tickers with cumulative graphs**, both for a
  single program and across all programs
- Improved the error logging for donation settings
- Added a toggle to hide incomplete financial aid requests
- Stripe payment fields are now validated before a charge is attempted, and the
  transaction submission endpoint only accepts POST, so it cannot be triggered
  by crawlers
- Fixed the Stripe setup check reporting success when no keys are configured,
  and crashes when the Stripe settings tag is missing
- Credit card settings are now read as program tags rather than global tags

Accounts and profiles
~~~~~~~~~~~~~~~~~~~~~
- **Password strength is now validated on registration and password change.**
  Users will be prevented from choosing weak passwords, which was previously
  allowed
- **Email address and username availability are now checked live during account
  creation**, instead of only on submit
- Account activation tokens are now signed rather than stored in plain text, and
  password recovery uses Django's built-in token generator
- Added inline editing of a user's name and email address on the user view page
- The user view page now shows starred classes, falls back to the current
  program for users with no profile, and no longer crashes when no username is
  given
- Role names are now capitalized consistently
- Login form fields are now marked as required in the markup
- Account disable actions now only accept POST
- Added validation of first and last names, of student grade in the student
  information form, and a check that a student's email does not match their
  parent or emergency contact email
- Added a data migration that cleans up duplicate registration profiles, and
  profiles are no longer saved as a side effect of being looked up
- Fixed the layout of the affiliation field, the merge accounts form, and the
  statistics form
- Fixed the account deactivation module

User search and permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **Permissions can now be granted to the users matching a saved user search
  filter**, rather than only to an entire user role
- Added equity outreach cohorts, exposed as user lists for targeted outreach
- Common searches for user types that a program does not use are now hidden
- Improved the error handling in the user search controller
- Added CSRF protection to the user search filter and list selector forms
- Fixed combination queries in the user search controller
- Improved the performance of the student registration search in the Django admin
- Volunteer usernames are now sanitized

Statistics
~~~~~~~~~~
- **Added a K-12 school database**: state and city fields, server-side
  autocomplete, a statistics form, and a management command for bulk importing
  schools from NCES data
- Fixed a large number of statistics bugs, including the zip code statistics
  (which previously included non-student users), the registration type filters,
  the school filter, null graduation years in the demographics, and a crash on
  the program type field
- Fixed the statistics query form erroring when no programs exist
- Substantially reduced the number of database queries the statistics pages
  make, so they load much faster

Website content
~~~~~~~~~~~~~~~
- **Images can now be uploaded directly from the page editor.** Uploads are
  validated (file extension, content type, and a 5 MB limit) and stored under
  generated filenames, replacing the old file browser workaround. This works on
  the page edit form, for inline editing, and in the communications panel
- **Added a version history interface for editable pages**: list, preview, and
  restore any previous version. Restoring creates a new version rather than
  discarding history
- **Added a front-end interface for managing uploaded site media**
- The editor's alignment buttons now apply only to the selected text
- Editable pages now redirect with a message instead of showing a bare
  permission error when the user cannot edit them
- Fixed the page editor breaking on HTML comments, the default content not being
  loaded into the edit page, and a URL handling bug that broke ``.html`` pages
- Fixed the recovery of deleted pages, which previously depended on a specific
  navigation category existing
- Fixed the handling of base64-encoded images
- The file browser now handles file extensions case-insensitively
- Media filenames are now stored with consistent case

Custom forms
~~~~~~~~~~~~
- **Modernized custom forms**: removed the bundled legacy jQuery, upgraded the
  validation library, and rewrote the validation script
- Custom form titles can no longer be left empty
- Form response data is now only accessible to the form's owners
- Custom form questions now have a consistent default order
- Added the missing labels to the form controls on the form creation page, and
  fixed the alignment of the minimum and maximum fields
- Fixed the custom forms landing page erroring when a linked object has been
  deleted
- Reduced the number of database queries needed to fetch form responses
- The Formstack medical form module now shows whether the form has been
  completed

Accessibility
~~~~~~~~~~~~~
- Added a skip-to-main-content link and semantic landmark regions (``<main>``,
  ``<nav>``, ``<aside>``) to the base template, along with a page language
  attribute
- Repaired broken markup and added missing labels across the profile,
  registration, and survey forms
- Removed the styles that suppressed focus outlines and added a global
  ``:focus-visible`` style, so keyboard focus is always visible (WCAG 2.1 SC
  2.4.7)
- Improved image alt text throughout the templates
- Added keyboard accessibility to module management
- Made the privacy policy link visually distinguishable
- Fixed a number of template HTML validity problems, including the logout page

Admin documentation
~~~~~~~~~~~~~~~~~~~
- **The admin documentation is now readable inside the website**, at
  ``/manage/docs``, instead of requiring a trip to GitHub. The management index
  also shows a preview of the latest release notes
- Added a central "customizing the website" index covering editable pages, tags,
  themes, and template overrides
- Added an admin-facing guide to tags and (S)CRMI
- The droplets admin bar now links to the documentation

Security
~~~~~~~~
- Added Django's ``SecurityMiddleware`` and hardened the transport and cookie
  settings
- Fixed an open redirect in the class administration views
- Removed all use of ``eval()`` and ``exec()``, including a vulnerable ``eval()``
  in the AJAX tools script
- Replaced SHA-1, MD5, and insecure random number generation with SHA-256 and
  cryptographically secure randomness
- Removed room location data from the public class information endpoint
- Blocked public access to the ``/server-status`` and ``/server-info`` endpoints
- Fixed a code injection vulnerability in the Formstack autopopulation
- Fixed a stored cross-site-scripting issue in page editing

Minor new features
~~~~~~~~~~~~~~~~~~
- Improved the error pages: a shared base template, a user-friendly message with
  the technical detail in a second tier, and a button for reporting the error
- Added a confirmation on the contact form submit button
- Number inputs no longer change value when the mouse wheel is scrolled over them
- Added a redirect for ``/myesp``
- Removed the remnants of the mailing labels module and the deprecated miniblog
- Removed the debug output that was left in the production JavaScript assets

Minor bug fixes
~~~~~~~~~~~~~~~
- Fixed a login page crash caused by an uninitialized variable
- Fixed the user selector defaulting to the wrong user type when viewing student
  schedules
- Fixed the class capacity calculation when no maximum class size or room
  capacity is set
- Fixed a crash when sorting or comparing classes, caused by classes not being
  hashable
- Fixed a division-by-zero error when there are no priority requests
- Fixed the "archives" pages for teachers and programs
- Fixed the caching dependencies in a number of places, including grade caches
  and list counts, so stale data is no longer shown after a change
- Fixed oversized values being rejected by memcached, by chunking large cache
  entries
- Fixed a ``Vary: Cookie`` header bug that prevented cacheable pages from being
  cached
- Fixed the CSRF failure page, which now parses the path correctly and includes
  the program context
- Fixed several pages that returned a server error when given a stale or invalid
  object ID, including the resource module edit and delete flows
- Fixed dates in program models being evaluated once at import time rather than
  when used
- Fixed a race in the creation of program module records
- Fixed the validation of generic foreign key fields
- Fixed the missing search icon in the admin foreign key widget

Development changes
===================

- Docker is now the supported development environment, replacing Vagrant.
  Migrations run automatically on container start, and Apple silicon (ARM) hosts
  are supported
- Test suites now run under pytest, with parallel execution and coverage
  targets enforced in CI. A large number of previously untested modules now have
  test coverage, along with shared test factories and full-pipeline integration
  tests
- Added a ``seed_dummy_data`` management command and helpers for generating bulk
  fake data for development
- Added pre-commit hooks with a shared flake8 configuration
- Removed the remaining Python 2 compatibility code, and converted string
  formatting to f-strings throughout
- Replaced hard-coded URLs in templates with named URL tags
- Added documentation for setting up a new server and for creating your first
  program after a local setup

Dependency changes
~~~~~~~~~~~~~~~~~~
- Upgraded Django (1.11.29 -> 5.2.16 LTS), in incremental stages
- Upgraded Python (3.7 -> 3.12)
- Upgraded Bootstrap (2.3.2 -> 5.3.3) and added Bootstrap Icons (1.11.3),
  Bootswatch (5.3.3), and dart-sass; removed the LESS toolchain
- Upgraded Knockout.js (2.3.0 -> 3.5.1) and Select2 (3.4.3 -> 4.1.0)
- Upgraded jQuery Validation (-> 1.19.5, now loaded from a CDN rather than
  bundled) and removed the bundled copy of jQuery 1.5.1
- Upgraded django-debug-toolbar (1.11.1 -> 5.2.0)
- Upgraded django-extensions (1.8.1 -> 4.1)
- Upgraded django-filebrowser-no-grappelli (3.8.0 -> 4.0.2)
- Upgraded django-formtools (2.1 -> 2.7)
- Upgraded django-localflavor (1.1 -> 3.1)
- Upgraded django-recaptcha (2.0.6 -> 3.0.0)
- Upgraded django-reversion (1.10.0 -> 5.0.2)
- Upgraded django-sendgrid-v5 (0.9.0 -> 1.2.4)
- Upgraded django-vanilla-views (1.0.4 -> 3.0.0)
- Upgraded bleach (6.0.0 -> 6.4.0)
- Upgraded docutils (0.12 -> 0.19)
- Upgraded flake8 (3.9.2 -> 7.1.1)
- Upgraded ipython (7.34.0 -> 8.12.3)
- Upgraded Markdown (2.3.1 -> 3.8.1)
- Upgraded numpy (1.16.6 -> 1.26.4)
- Upgraded pillow (8.3.2 -> 12.3.0)
- Upgraded psycopg2 (2.8.6 -> 2.9.9)
- Upgraded pycurl (7.19.5.1 -> 7.45.4)
- Upgraded py3dns (3.2.1 -> 4.0.2)
- Upgraded Pygments (2.10.0 -> 2.20.0)
- Upgraded pytz (2015.4 -> 2023.3)
- Upgraded selenium (2.44.0 -> 4.9+)
- Upgraded setuptools (57.5.0 -> 83.0.0)
- Upgraded stripe (2.60.0 -> 7.5.0)
- Upgraded werkzeug (unpinned -> 3.1.6)
- Upgraded django-argcache and django-admin-tools to tagged releases, and
  switched django-form-utils to a maintained fork
- Replaced xlwt with openpyxl for form and survey exporting
- Replaced pylibmc with pymemcache
- Replaced django-localflavor's phone number field with
  django-phonenumber-field
- Added Faker, pytest, pytest-cov, pytest-django, and pytest-xdist
- Removed raven (Sentry), pyinotify, and the vendored YUI and jsTree libraries

Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Duplicating Objects in the Admin Panel
======================================

Object pages in the admin panel now have a "Save as new" button, which saves your edits as a brand new object instead of overwriting the one you opened. To create several similar objects (line item types, events, permissions, class flag types, and so on), open one that already exists, change the fields that differ, and click "Save as new". Any inline objects listed on the page are copied along with it.

Note that on pages that have this button, it takes the place of "Save and add another"; the blank add form is still available from the "Add" button on the object list page.

A few pages do not offer the button, because a copy would either be unsaveable or would be a record of something that never happened: user accounts, Cybersource postbacks, sent email, financial aid requests, grade change requests, student applications (along with their responses and reviews), and the Formstack application pages.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.
- ``ESPAdminSite.register`` now sets ``save_as = True`` on every registered ``ModelAdmin``. Admins whose add form cannot produce a saveable duplicate (a required field that is readonly, excluded, or ``editable=False``) set ``save_as = False`` for themselves; ``esp/esp/tests/test_admin_save_as.py`` checks that the two lists agree.

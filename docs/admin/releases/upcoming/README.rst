Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.0.14.
- Updated dependencies for Django 5.0 compatibility: ``django-debug-toolbar`` 4.4.0 → 5.0.1.
- Updated deprecated ``assertFormError`` test usage to Django 5.0-compatible form-object assertions in ``esp/program/modules/tests/programprintables.py`` and ``esp/users/tests.py``.

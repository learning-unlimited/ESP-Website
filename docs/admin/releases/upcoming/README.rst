Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Form Field Selectors
====================

The tags that control which optional fields appear on the profile and teacher class
registration forms are now two-column selectors on the tag settings pages.

The tags behind them have been renamed from ``*_hide_fields`` (a list of the fields to
remove) to ``*_active_fields`` (a list of the fields to keep):
``student_profile_active_fields``, ``teacher_profile_active_fields``,
``guardian_profile_active_fields``, ``educator_profile_active_fields``,
``volunteer_profile_active_fields``, and ``teacherreg_active_fields``.

A migration converts any ``*_hide_fields`` tag you have set, so no action is needed to
upgrade.

Bug Fixes
=========

- Director email addresses and outgoing "From" addresses now accept ``learningu.org`` at any subdomain depth. The rule previously allowed at most one subdomain label, so an address like ``info@a.b.learningu.org`` was rejected even though the director email help text has always described any valid subdomain as acceptable. This applies to the program creation and program settings forms, the ``director_email`` model validator, and the "From" address checks used by the comm panel and automated mail.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

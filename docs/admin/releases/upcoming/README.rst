Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Class Registration Drafts
=========================

Teachers can now save an incomplete class registration form as a draft and come back to it later. The class registration form gains a "Save as a Draft" button, which stores whatever has been filled in so far without running any of the usual validation, and a "Discard Draft" button for throwing that work away.

A draft is held as a class with the new "draft" status. Drafts are invisible to students, are not counted as submitted classes for admin teacher lists or teacher registration progress, and do not take part in teacher conflict or time-commitment calculations. Each teacher gets one draft per registration flow (regular classes and open classes are tracked separately); submitting the form promotes that draft into a normal unreviewed class.

Bug Fixes
=========

- Director email addresses and outgoing "From" addresses now accept ``learningu.org`` at any subdomain depth. The rule previously allowed at most one subdomain label, so an address like ``info@a.b.learningu.org`` was rejected even though the director email help text has always described any valid subdomain as acceptable. This applies to the program creation and program settings forms, the ``director_email`` model validator, and the "From" address checks used by the comm panel and automated mail.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

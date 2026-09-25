Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Teacher Schedule Deadline
=========================

A new ``Teacher/Classes/Schedule`` deadline controls whether teachers and moderators can see the room and time assigned to their sections on the teacher class registration page. While the deadline is closed, those assignments (along with the "Detailed Status" time blocks and the attendance links that go with them) are replaced with a note that the schedule is not yet available; everything else on the page is unchanged.

The deadline is created default-open for new programs, and is backfilled default-open for existing programs, so nothing changes until an administrator closes it. Close it while scheduling is in progress to keep teachers from seeing assignments that may still change, and re-open it when the schedule is final. Note that ``Teacher/All`` and ``Teacher/Classes/All`` imply this permission, so they must not be open at the same time for it to have any effect.

Lunch Constraints: Warn or Enforce
==================================

Schedule constraints (e.g., lunch constraints generated from the "Lunch Constraints" management page) can now either warn students or block them when they try to add a class that **newly** violates a constraint. Previously existing overrides (e.g., an enrollment by an admin) no longer block a student from making new changes.

The "Lunch Constraints" page has a new "enforce" checkbox:

- **Unchecked (warn).** Students see a note at the top of their schedule listing what it is missing (e.g., "You need to choose a lunch period on Saturday"), on the main student registration page and in the onsite webapp. The note updates as soon as they add or remove a class. Nothing is ever blocked.
- **Checked (enforce).** The same note appears, and in addition a student is refused any schedule change that would *newly* break a constraint (e.g., dropping their only lunch period while they still have classes before and after it). A student whose schedule already violates a constraint is never blocked, so they can always work their way back to a valid schedule instead of being stuck.

Old programs will continue to enforce existing constraints. New programs will default to warnings unless configured otherwise.

The onsite class changes grid now reports the same notifications but can be overridden using the "Override size limits and schedule constraints" checkbox.

Bug Fixes
=========

- Director email addresses and outgoing "From" addresses now accept ``learningu.org`` at any subdomain depth. The rule previously allowed at most one subdomain label, so an address like ``info@a.b.learningu.org`` was rejected even though the director email help text has always described any valid subdomain as acceptable. This applies to the program creation and program settings forms, the ``director_email`` model validator, and the "From" address checks used by the comm panel and automated mail.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

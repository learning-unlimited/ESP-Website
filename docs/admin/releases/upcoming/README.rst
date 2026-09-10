Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Teacher Schedule Deadline
=========================

A new ``Teacher/Classes/Schedule`` deadline controls whether teachers and moderators can see the room and time assigned to their sections on the teacher class registration page. While the deadline is closed, those assignments (along with the "Detailed Status" time blocks and the attendance links that go with them) are replaced with a note that the schedule is not yet available; everything else on the page is unchanged.

The deadline is created default-open for new programs, and is backfilled default-open for existing programs, so nothing changes until an administrator closes it. Close it while scheduling is in progress to keep teachers from seeing assignments that may still change, and re-open it when the schedule is final. Note that ``Teacher/All`` and ``Teacher/Classes/All`` imply this permission, so they must not be open at the same time for it to have any effect.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

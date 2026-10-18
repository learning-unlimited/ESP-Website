Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Teacher Schedule Deadline
=========================

A new ``Teacher/Classes/Schedule`` deadline controls whether teachers and moderators can see the room and time assigned to their sections on the teacher class registration page. While the deadline is closed, those assignments (along with the "Detailed Status" time blocks and the attendance links that go with them) are replaced with a note that the schedule is not yet available; everything else on the page is unchanged.

The deadline is created default-open for new programs, and is backfilled default-open for existing programs, so nothing changes until an administrator closes it. Close it while scheduling is in progress to keep teachers from seeing assignments that may still change, and re-open it when the schedule is final. Note that ``Teacher/All`` and ``Teacher/Classes/All`` imply this permission, so they must not be open at the same time for it to have any effect.

Teacher Registration Layout
===========================

The teacher registration module pages (profile, biography, availability, acknowledgement, moderator signup, teacher events, custom forms and quizzes, surveys, and the class management pages such as coteachers, class documents and rosters) now share the layout of the teacher registration main page. When the checklist is enabled, it (along with any other registration requirements) stays visible in a column beside the page content on wide screens, or above the content on narrow screens, so teachers can see their progress from any step. In progress bar mode, the progress bar is still shown across the top of these pages. The class registration form no longer shows the checklist, so the form has the full page width. Nothing about how the modules work has changed.

Bug Fixes
=========

- Director email addresses and outgoing "From" addresses now accept ``learningu.org`` at any subdomain depth. The rule previously allowed at most one subdomain label, so an address like ``info@a.b.learningu.org`` was rejected even though the director email help text has always described any valid subdomain as acceptable. This applies to the program creation and program settings forms, the ``director_email`` model validator, and the "From" address checks used by the comm panel and automated mail.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.
- Teacher registration templates now extend ``program/modules/teacherregcore/teacher_module_base.html`` (content goes in the ``module_content`` block) instead of ``program/modules/module_base.html``, which is still used by student module pages. The class registration form (``classedit.html``) now extends ``main.html`` directly. The checklist context for both the teacher main page and module pages comes from ``esp.program.modules.checklist.get_checklist_context``. The ``teacherregcore-mainpage.css`` stylesheet was renamed to ``teacherreg-layout.css``.

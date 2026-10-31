Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

Class Registration Drafts
=========================

Teachers can now save an incomplete class registration form as a draft and come back to it later. The class registration form gains a "Save as a Draft" button, which stores whatever has been filled in so far without running any of the usual validation, and a "Discard Draft" button for throwing that work away.

A draft is held as a class with the new "draft" status. Drafts are invisible to students, are not counted as submitted classes for admin teacher lists or teacher registration progress, and do not take part in teacher conflict or time-commitment calculations. Each teacher gets one draft per registration flow (regular classes and open classes are tracked separately); submitting the form promotes that draft into a normal unreviewed class.

Teacher Schedule Deadline
=========================

A new ``Teacher/Classes/Schedule`` deadline controls whether teachers and moderators can see the room and time assigned to their sections on the teacher class registration page. While the deadline is closed, those assignments (along with the "Detailed Status" time blocks and the attendance links that go with them) are replaced with a note that the schedule is not yet available; everything else on the page is unchanged.

The deadline is created default-open for new programs, and is backfilled default-open for existing programs, so nothing changes until an administrator closes it. Close it while scheduling is in progress to keep teachers from seeing assignments that may still change, and re-open it when the schedule is final. Note that ``Teacher/All`` and ``Teacher/Classes/All`` imply this permission, so they must not be open at the same time for it to have any effect.

Form Field Selectors
====================

The tag settings that choose which questions to drop from the profile forms and
the teacher class registration form (``teacher_profile_hide_fields``,
``student_profile_hide_fields``, ``volunteer_profile_hide_fields``,
``educator_profile_hide_fields``, ``guardian_profile_hide_fields`` and
``teacherreg_hide_fields``) are now two-column selectors: fields start in an
"Available" column and the ones you move into the "Chosen" column are the ones
hidden from the form. The settings themselves are unchanged, so any values you
have set already carry over and keep working.

Weighted Room Filters in the Scheduler
======================================

The Room Filters tab of the AJAX scheduler can now rank rooms by how closely they match, instead of only hiding the rooms that don't match exactly.

- Each room filter (minimum and maximum capacity, resource, and name) has a weight, which defaults to 1. A higher weight makes that filter count for more, and a weight of 0 ignores it.
- Each room gets a match score: 1 minus the weighted average of its squared distances from the active filters. A capacity filter's distance grows with how far the room is from the requested size. A resource or name filter counts as either a match or a miss.
- Rooms are listed best match first. Rooms that fully match are highlighted in green, and the rest show their match percentage next to the room name and in the room's tooltip.
- A new "Match Threshold" slider hides rooms that score below the chosen percentage. It defaults to 100%, so the filters work exactly as before until you move the slider down to see near matches.
- A new "Free at Timeslots" filter, which also has a weight, scores rooms by whether they are free in every timeslot you choose by clicking the timeslot headers in the grid. Chosen headers are outlined, and the Room Filters tab lists them with a Clear button. A room counts as free in a timeslot if it is available then and holds no class other than the selected one. A room that is free in only some of the chosen timeslots gets partial credit, so it can still appear once you lower the match threshold. The filter updates as classes are scheduled, including by other users.
- A new "Room fits the selected class" filter, which also has a weight, scores rooms by whether the selected class has at least one valid placement there (i.e., a green square). The room the class is already scheduled in always counts as a fit. This filter has no effect when no class is selected. It is off by default, since hiding rooms also hides classes you may want to Ctrl/Cmd+click to swap with.

Bug Fixes
=========

- The teacher custom form, teacher quiz and student custom form module pages now check required fields and field formats in the browser before submitting, as standalone custom forms do. The date check on all custom forms now also accepts the format the site re-displays saved dates in (such as "2026-11-14"). Phone numbers are no longer checked in the browser, which rejected international numbers the site accepts; the server still checks them.
- The "First Step" and "Prev Step" buttons on custom forms no longer require the current page to be filled in correctly, so users can go back without completing it first.
- Pressing Enter on a later page of a custom form (standalone, or a teacher or student registration step) now goes to the next page instead of back a page.
- Director email addresses and outgoing "From" addresses now accept ``learningu.org`` at any subdomain depth. The rule previously allowed at most one subdomain label, so an address like ``info@a.b.learningu.org`` was rejected even though the director email help text has always described any valid subdomain as acceptable. This applies to the program creation and program settings forms, the ``director_email`` model validator, and the "From" address checks used by the comm panel and automated mail.
- Teachers can now edit their class website pages inline. Inline editing controls and the "Edit this page" button were previously only shown to administrators, even though teachers of a class have permission to edit its pages. Logged-in non-admins now see the editing controls for any page or inline text block they have permission to edit, and nothing else.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

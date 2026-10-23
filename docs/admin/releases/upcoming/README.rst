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

Class Description Images
========================

Teachers can now add a picture to their class description. Turn this on per program with the new ``enable_class_description_images`` tag setting (off by default). While it is on, the class registration form gains an optional "Class Description Image" upload right below the description; images larger than 500x500 pixels are shrunk to fit. When editing a class, the current picture is kept unless a new one is uploaded or "Clear" is ticked, and pictures are kept when a class is saved as a draft. Pictures are not carried over when copying a class from a previous program.

The picture appears alongside the description in the class catalog, the two-phase student registration catalog, and the onsite webapp catalog. Turning the setting off hides all pictures again without deleting them.

Bug Fixes
=========

- Uploading a teacher bio picture no longer fails with a server error. The image resizing code used a Pillow constant that was removed in Pillow 10.
- Director email addresses and outgoing "From" addresses now accept ``learningu.org`` at any subdomain depth. The rule previously allowed at most one subdomain label, so an address like ``info@a.b.learningu.org`` was rejected even though the director email help text has always described any valid subdomain as acceptable. This applies to the program creation and program settings forms, the ``director_email`` model validator, and the "From" address checks used by the comm panel and automated mail.
- Teachers can now edit their class website pages inline. Inline editing controls and the "Edit this page" button were previously only shown to administrators, even though teachers of a class have permission to edit its pages. Logged-in non-admins now see the editing controls for any page or inline text block they have permission to edit, and nothing else.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

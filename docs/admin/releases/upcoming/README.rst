Refund Feature
==============

A new student refund feature provides administrators with the ability to instantly issue partial or full refunds directly through the website using the Stripe API. 

Administrators can navigate to the refunds page (linked under "Quick Links" in the management dashboard) and search for a student to view their transactions. The interface clearly displays the original transaction amount, how much has already been refunded, and the remaining amount available to refund. 

When a refund is submitted, it is processed synchronously via Stripe, and the results (success or failure) are shown on a confirmation screen. In either case, the CFO is sent an email indicating the status of the refund.

New Customization Tags
======================

Several previously hard-coded behaviors are now configurable by tag. Each tag
defaults to the existing behavior, so nothing changes unless it is set.

- ``student_profile_show_guardian_info`` (global, student registration): set to ``False`` to drop the parent/guardian contact section from the student profile form. This was not previously possible, because ``student_profile_hide_fields`` only offers fields that are not required.
- ``onsite_show_paid_field`` (global, onsite): set to ``False`` to hide the "paid in full" checkbox on the onsite registration form.
- ``volunteer_label_comments`` (per-program, volunteer): overrides the label of the volunteer form's comments field, complementing the existing ``volunteer_help_text_comments`` tag.
- ``volunteer_help_text_requests`` (per-program, volunteer): overrides the help text of the volunteer form's timeslots field.
- ``volunteer_help_text_confirm`` (per-program, volunteer): overrides the text of the volunteer form's confirmation checkbox. The value is treated as plain text and the default red styling is kept.
- ``bigboard_graph_drop_beg``, ``bigboard_graph_drop_end``, and ``bigboard_graph_min_points`` (per-program, general management): control how many data points are trimmed from each end of the big board's registration graph series, and how many points a series needs before it is plotted. These were previously hard-coded as 4, 0, and 5 respectively.

Developer Notes
===============

- Upgraded Django from 4.2.30 to 5.2.14 (LTS).
- Updated dependencies for Django 5.2 compatibility: ``django-debug-toolbar`` 5.1.0 → 5.2.0.

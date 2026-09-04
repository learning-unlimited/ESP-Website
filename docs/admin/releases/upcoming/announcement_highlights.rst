=================================================
 Stable Release 17 — headline changes for admins
=================================================

.. contents:: :local:

About this list
===============

A working list of the largest **user-facing** changes queued up for stable
release 17, intended as source material for the announcements we make to
chapter admins over the coming months.

Scope: everything merged to ``main`` after the Release 16 **October 2025
patch** (see ``docs/admin/releases/16/README.rst``). Roughly 650 pull requests
landed in that window; the ~40 PRs merged between the ``sr16`` tag and October
2025 were already shipped and announced as part of the Release 16 June and
October patches, so they are deliberately excluded here.

Also deliberately excluded: the Django 2 → 5.2, Python 3.7 → 3.12, and
Bootstrap-adjacent dependency upgrades, the ~200 test-coverage PRs, CI/Docker
work, and the large number of internal refactors. Those are significant, but
they are not what admins will notice.

Each entry lists the primary PR(s). Screenshots are not included — most of
these are best captured live against a demo program.

Headline features
=================

1. The theme system rebuilt on Bootstrap 5, with Bootswatch themes
------------------------------------------------------------------

The single biggest visual change in the release. Release 16 noted that we were
"still using an old version of Bootstrap, but we plan to upgrade that in the
future" — this is that upgrade, done in four staged phases, taking the site
from Bootstrap 2.3.2 all the way to 5.3.3.

- Bootstrap is now an npm dependency rather than 42 committed LESS files, and
  the theme pipeline moved from LESS to SCSS (dart-sass).
- Glyphicons were replaced with Bootstrap Icons.
- **Bootswatch themes**: admins can pick a Bootswatch theme from the theme
  editor as the *base* for their site, and the existing colour customizer then
  layers on top of it. Every customizer field (scaffolding, links, typography,
  buttons, and each theme's navbar/sidebar/tab colours) is derived from the
  selected Bootswatch palette, with contrast-aware fallbacks. Only variables
  the admin actually changes are overridden.
- The legacy LESS pipeline has been removed entirely.

PRs: `#5806 <https://github.com/learning-unlimited/ESP-Website/pull/5806>`_
(Phase 1, BS2→3 + npm),
`#5816 <https://github.com/learning-unlimited/ESP-Website/pull/5816>`_
(Phase 2, BS3→4 + LESS→SCSS),
`#5817 <https://github.com/learning-unlimited/ESP-Website/pull/5817>`_
(Phase 3, BS4→5 + Bootstrap Icons + Bootswatch),
`#5862 <https://github.com/learning-unlimited/ESP-Website/pull/5862>`_
(Phase 4, per-variable customization on top of Bootswatch),
`#5936 <https://github.com/learning-unlimited/ESP-Website/pull/5936>`_
(remove legacy LESS pipeline)

*Screenshot suggestion: the theme editor with the Bootswatch dropdown open,
plus a before/after of one chapter's front page.*

2. Registration module timeline (module management overhaul)
------------------------------------------------------------

The module management page has been rebuilt around an interactive timeline
grid. Instead of a flat sortable list plus separate deadline editing, admins
see modules laid out against program dates and can drag to reorder, edit
required/label/link-title settings inline, and open a side drawer to add
modules.

- ``ProgramModuleObj`` now inherits from ``ExpirableModel``, so each module
  carries its own start/end dates, and ``getModules()`` filters by time for
  non-admins.
- Modules whose order or required status is enforced by the backend are locked
  in the UI, so illegal drags are prevented up front rather than silently
  undone on save; conflict detection warns about overlapping windows.
- Module permissions are synchronised automatically from timeline dates, and
  new programs are created with sensible initial module permissions and dates.
- Full keyboard navigation and accessibility pass, plus a confirmation step
  when a change would affect students who are actively registering.
- Module link titles are now editable per program.

PRs: `#5810 <https://github.com/learning-unlimited/ESP-Website/pull/5810>`_,
`#5834 <https://github.com/learning-unlimited/ESP-Website/pull/5834>`_,
`#5841 <https://github.com/learning-unlimited/ESP-Website/pull/5841>`_,
`#5842 <https://github.com/learning-unlimited/ESP-Website/pull/5842>`_,
`#5856 <https://github.com/learning-unlimited/ESP-Website/pull/5856>`_,
`#5859 <https://github.com/learning-unlimited/ESP-Website/pull/5859>`_,
`#5881 <https://github.com/learning-unlimited/ESP-Website/pull/5881>`_,
`#5895 <https://github.com/learning-unlimited/ESP-Website/pull/5895>`_,
`#5939 <https://github.com/learning-unlimited/ESP-Website/pull/5939>`_,
`#4160 <https://github.com/learning-unlimited/ESP-Website/pull/4160>`_,
`#4059 <https://github.com/learning-unlimited/ESP-Website/pull/4059>`_.
Developer docs: `#5941
<https://github.com/learning-unlimited/ESP-Website/pull/5941>`_

3. Program management dashboard modernization
----------------------------------------------

The management dashboard (the page admins land on for a program) was
redesigned: the vertical setup-steps table became a horizontal Gantt-style
timeline, module categories collapse and expand, and link captions became
hover tooltips for a cleaner button grid.

On top of that, a **search box** now finds management pages by name and
keyword — modules opt in with search metadata, so searching "nametags" or
"check-in" jumps straight there. Many more management buttons were promoted
into featured categories, categories were reorganised (including a new
Financial and Accounting category), and empty categories are hidden. The admin
toolbar links are now configurable through theme settings.

PRs: `#4503 <https://github.com/learning-unlimited/ESP-Website/pull/4503>`_,
`#4255 <https://github.com/learning-unlimited/ESP-Website/pull/4255>`_,
`#5830 <https://github.com/learning-unlimited/ESP-Website/pull/5830>`_,
`#4586 <https://github.com/learning-unlimited/ESP-Website/pull/4586>`_

4. Refunds, refund accounting, and fundraising tickers
-------------------------------------------------------

Admins can now issue partial or full **Stripe refunds directly from the
website**. The refunds page (linked under Quick Links on the management
dashboard) lets you search for a student, see each transaction's original
amount, amount already refunded, and remaining refundable amount, and submit a
refund that is processed synchronously through Stripe. The CFO is emailed
either way, and a confirmation screen reports success or failure.

Refunds also now generate proper accounting entries: a refund line item type,
``amount_refunded()`` tracking, and ``amount_due()`` accounting for refunds, so
the accounting page and transaction records reflect them correctly. The credit
card revenue summary was reworked with time-based fetching and program
isolation, and the accounting pages gained donation and admission **tickers
with cumulative graphs**, both per-program and across all programs.

PRs: `#4221 <https://github.com/learning-unlimited/ESP-Website/pull/4221>`_
(refund page),
`#4568 <https://github.com/learning-unlimited/ESP-Website/pull/4568>`_
(refund accounting entries),
`#4945 <https://github.com/learning-unlimited/ESP-Website/pull/4945>`_
(refund display/sign fixes),
`#5036 <https://github.com/learning-unlimited/ESP-Website/pull/5036>`_
(credit card revenue summary),
`#5568 <https://github.com/learning-unlimited/ESP-Website/pull/5568>`_
(donation and admission tickers)

*This is the one feature already written up in* ``docs/admin/releases/upcoming/README.rst``.

5. Recurring class scheduling
------------------------------

The AJAX scheduler now supports classes that meet more than once — the same
section scheduled into several occurrences rather than one contiguous block.
Recurring controls appear in the scheduler UI and section info panel (with a
legend entry), multi-block recurring classes are handled correctly, and the
recurring meetings render in student schedules, the onsite schedule view, and
teacher registration displays. An opt-in program tag adds one LaTeX row per
occurrence in printed student schedules.

PR: `#5865 <https://github.com/learning-unlimited/ESP-Website/pull/5865>`_
(fixes #4852, closes #3217 and #3826)

6. Admin documentation embedded in the website
-----------------------------------------------

Admins no longer have to go to GitHub to read the admin docs. A new
``/manage/docs`` page renders the admin documentation inside the site
(admin-only), and the management index shows a preview of the latest release
notes. New docs were also written: a central "customizing" index covering QSD,
Tags, Themes, and Template Overrides, and an admin-facing guide to Tags and
(S)CRMI. The droplets admin bar links to the documentation directly.

PRs: `#4487 <https://github.com/learning-unlimited/ESP-Website/pull/4487>`_,
`#4467 <https://github.com/learning-unlimited/ESP-Website/pull/4467>`_,
`#4647 <https://github.com/learning-unlimited/ESP-Website/pull/4647>`_

7. Class flags: teacher-visible, resolvable, and automatic
-----------------------------------------------------------

Three substantial additions to class flags:

- **Teacher-visible flags.** Flag types can be marked visible to teachers and
  can optionally email all of a class's teachers when such a flag is added.
  Visible flags show on the teacher class list and class status pages.
- **Resolvable flags.** Flags can be resolved rather than deleted, keeping the
  record (with who resolved it and when) in the system. Class search gained a
  resolved-status filter, and flag audit trails survive user deletion.
- **Auto-flag rules.** A new engine lets admins define query-based rules that
  automatically apply a flag (with an optional comment and teacher
  notification) to classes as they are created. Rules are created from the
  class search page and can optionally be back-applied to all existing
  matching classes.

PRs: `#4214 <https://github.com/learning-unlimited/ESP-Website/pull/4214>`_,
`#4575 <https://github.com/learning-unlimited/ESP-Website/pull/4575>`_,
`#4975 <https://github.com/learning-unlimited/ESP-Website/pull/4975>`_

8. Content editing: image uploads, page history, and a media manager
---------------------------------------------------------------------

- **Image upload in the editor.** The Jodit WYSIWYG editor now uploads images
  directly (validated extension, content type, and 5 MB limit; UUID
  filenames), replacing the old filebrowser workaround. Available on the QSD
  edit page, inline QSD editing, and in the communications panel.
- **QSD version history.** A UI for listing, previewing, and restoring
  previous versions of any QSD page, built on the existing revision tracking.
  Restoring creates a new revision rather than discarding history.
- **Site media manager.** A front-end UI for browsing and managing uploaded
  site media.
- Plus fixes to Jodit alignment buttons (now apply to the selection only) and
  to QSD editing with HTML-comment edge cases.

PRs: `#4249 <https://github.com/learning-unlimited/ESP-Website/pull/4249>`_,
`#4358 <https://github.com/learning-unlimited/ESP-Website/pull/4358>`_,
`#4525 <https://github.com/learning-unlimited/ESP-Website/pull/4525>`_,
`#4603 <https://github.com/learning-unlimited/ESP-Website/pull/4603>`_,
`#4666 <https://github.com/learning-unlimited/ESP-Website/pull/4666>`_

9. Onsite and check-in improvements
------------------------------------

A broad set of improvements to day-of-program tools:

- Rapid check-in: search by first name, filtering, and clearer barcode
  visibility; barcode check-in also handles records and payment.
- Teacher check-in: teachers who checked in on a previous program day but not
  today are badged "prev-day" on the missing-teachers page, so admins know who
  probably just needs a reminder.
- Student attendance: an **Undo** button for accidentally marked attendance,
  which also reverses the automatic program check-in it created.
- The public "open classes" list was rebuilt — a real themed table with
  timeslot group headers, an empty state, a timeslot filter dropdown, and no
  more forced auto-scroll/auto-refresh.
- A class search box on the student onsite catalog page.
- The onsite ``schedule_students`` user search is now AJAX autocomplete.
- A schedule PDF download button on the onsite check-in interface.

PRs: `#4256 <https://github.com/learning-unlimited/ESP-Website/pull/4256>`_,
`#3952 <https://github.com/learning-unlimited/ESP-Website/pull/3952>`_,
`#4867 <https://github.com/learning-unlimited/ESP-Website/pull/4867>`_,
`#4914 <https://github.com/learning-unlimited/ESP-Website/pull/4914>`_,
`#4729 <https://github.com/learning-unlimited/ESP-Website/pull/4729>`_,
`#4524 <https://github.com/learning-unlimited/ESP-Website/pull/4524>`_,
`#4688 <https://github.com/learning-unlimited/ESP-Website/pull/4688>`_,
`#5256 <https://github.com/learning-unlimited/ESP-Website/pull/5256>`_

10. Batch student registration
-------------------------------

A new admin module that batch-registers a whole group of students into a class
section. Students are selected with the usual user search, sections are picked
from a list grouped by subject showing capacity and current enrolment, and
there is an override-full option. The result is a detailed per-student log
distinguishing conflicts, skips, and full sections. Registrations run in
chunked transactions so large batches do not time out.

PR: `#4202 <https://github.com/learning-unlimited/ESP-Website/pull/4202>`_

11. Per-program test accounts and test-data cleanup
----------------------------------------------------

Two features that make it much safer to rehearse a program:

- **AdminTestingModule** gives admins per-program test accounts they can log
  into ("testing mode", with a banner) and step out of again, without touching
  their own admin account.
- A **wipe test registration data** admin view removes a specific user's test
  registration data for a program, so you can re-run a registration rehearsal
  from a clean slate.

PRs: `#4422 <https://github.com/learning-unlimited/ESP-Website/pull/4422>`_,
`#4116 <https://github.com/learning-unlimited/ESP-Website/pull/4116>`_

12. Surveys: CSV import/export and redesigned pages
----------------------------------------------------

Survey questions can now be **exported to CSV and imported from CSV**, with a
downloadable template, validation, and a preview screen before committing the
import — a big time-saver for chapters that reuse question banks across
programs.

The survey management landing page and the favourite-classes results pages
were also redesigned, with clearer handling of the "no results yet" case,
tooltips, greyed-out buttons when no surveys exist, and fixes to histogram
rendering and long-answer question handling.

PRs: `#5149 <https://github.com/learning-unlimited/ESP-Website/pull/5149>`_,
`#4216 <https://github.com/learning-unlimited/ESP-Website/pull/4216>`_,
`#3948 <https://github.com/learning-unlimited/ESP-Website/pull/3948>`_,
`#4406 <https://github.com/learning-unlimited/ESP-Website/pull/4406>`_,
`#5151 <https://github.com/learning-unlimited/ESP-Website/pull/5151>`_,
`#5639 <https://github.com/learning-unlimited/ESP-Website/pull/5639>`_

13. Communications panel and email improvements
------------------------------------------------

- **Email template preview**: render an email with sample user data before
  sending, and send a test copy to yourself.
- A warning when a comm-panel email links to a *different* program — a common
  copy-paste mistake.
- Safety warnings on the mass mailer, and the artificial send delay removed.
- Class/section list recipients are de-duplicated, so nobody gets the same
  email twice.
- Fixes: images inserted into emails no longer use relative URLs; comm panel
  combination queries build correct filters; the grade-filter warning no longer
  always shows.

PRs: `#4372 <https://github.com/learning-unlimited/ESP-Website/pull/4372>`_,
`#4254 <https://github.com/learning-unlimited/ESP-Website/pull/4254>`_,
`#4311 <https://github.com/learning-unlimited/ESP-Website/pull/4311>`_,
`#4722 <https://github.com/learning-unlimited/ESP-Website/pull/4722>`_,
`#5677 <https://github.com/learning-unlimited/ESP-Website/pull/5677>`_,
`#5844 <https://github.com/learning-unlimited/ESP-Website/pull/5844>`_,
`#5912 <https://github.com/learning-unlimited/ESP-Website/pull/5912>`_

14. Schedule printing
----------------------

- **Asynchronous PDF generation** for large student schedule batches: a
  ``PrintableJob`` model, a job status page, and a cleanup command, so printing
  hundreds of schedules no longer blocks or times out the request.
- Students can **opt out of having a paper schedule printed**, via a checkbox
  on the student registration main page.
- Teacher schedules and nametags can be sorted by first class.
- An option to expire old print requests when opening the print-schedules page.
- Nametags now use the chapter's theme logo instead of a placeholder.
- Fixed column widths on the "Rooms by Time" printable, and a compact check-in
  view added to teacher list printables.

PRs: `#4673 <https://github.com/learning-unlimited/ESP-Website/pull/4673>`_,
`#4612 <https://github.com/learning-unlimited/ESP-Website/pull/4612>`_,
`#4663 <https://github.com/learning-unlimited/ESP-Website/pull/4663>`_,
`#4713 <https://github.com/learning-unlimited/ESP-Website/pull/4713>`_,
`#5101 <https://github.com/learning-unlimited/ESP-Website/pull/5101>`_,
`#5037 <https://github.com/learning-unlimited/ESP-Website/pull/5037>`_,
`#4357 <https://github.com/learning-unlimited/ESP-Website/pull/4357>`_

15. Accessibility pass
-----------------------

A sustained accessibility effort across the site: a skip-to-main-content link
and semantic landmark regions (``<main>``, ``<nav>``, ``<aside>``) in the base
template, ``lang`` attributes, repaired broken markup and missing ``<label>``
elements across profile/registration/survey forms, better image alt text,
removal of focus-outline suppressors in favour of a global ``:focus-visible``
style (WCAG 2.1 SC 2.4.7), keyboard accessibility for module management, and a
visually distinguishable privacy policy link.

PRs: `#4471 <https://github.com/learning-unlimited/ESP-Website/pull/4471>`_,
`#4593 <https://github.com/learning-unlimited/ESP-Website/pull/4593>`_,
`#4584 <https://github.com/learning-unlimited/ESP-Website/pull/4584>`_,
`#4427 <https://github.com/learning-unlimited/ESP-Website/pull/4427>`_,
`#4715 <https://github.com/learning-unlimited/ESP-Website/pull/4715>`_,
`#5668 <https://github.com/learning-unlimited/ESP-Website/pull/5668>`_,
`#5773 <https://github.com/learning-unlimited/ESP-Website/pull/5773>`_

16. Teacher events: interactive calendar and configurable event types
----------------------------------------------------------------------

Teacher event signup (interviews, training, etc.) got an interactive calendar
view instead of a flat list of times. Separately, teacher event types are no
longer hard-coded: an ``is_teacher_type`` flag on ``EventType`` (with a
backfill migration) means admins can configure which event types appear in
teacher signup and in the admin-facing teacher events management page.

PRs: `#5253 <https://github.com/learning-unlimited/ESP-Website/pull/5253>`_,
`#4291 <https://github.com/learning-unlimited/ESP-Website/pull/4291>`_

17. Student registration changes
---------------------------------

- **Class replacement with conflict confirmation**: registering for a class
  that conflicts with existing enrolments now offers to replace the conflicting
  class(es) after an explicit confirmation, in both the main catalog and the
  onsite webapp, instead of just refusing.
- **Cancel all classes for one day** button on the student schedule.
- Students with **approved financial aid can now cancel their registration**
  (previously blocked), with appropriate refund messaging.
- "Phase Zero" / "Student Lottery" is now consistently called **"Program
  Lottery"** in all user-facing text.
- Two-phase registration supports an optional **minimum number of classes**
  requirement (program tag).
- Lottery utility is now scaled by class duration.
- A registration checklist is shown on required module pages, so students can
  see where they are in the process from anywhere in registration.

PRs: `#4620 <https://github.com/learning-unlimited/ESP-Website/pull/4620>`_,
`#4395 <https://github.com/learning-unlimited/ESP-Website/pull/4395>`_,
`#4194 <https://github.com/learning-unlimited/ESP-Website/pull/4194>`_,
`#3999 <https://github.com/learning-unlimited/ESP-Website/pull/3999>`_,
`#4376 <https://github.com/learning-unlimited/ESP-Website/pull/4376>`_,
`#5632 <https://github.com/learning-unlimited/ESP-Website/pull/5632>`_,
`#4379 <https://github.com/learning-unlimited/ESP-Website/pull/4379>`_

18. Catalog improvements
-------------------------

- **Separate catalog pages by category**, controlled by a program tag: instead
  of one enormous page, students see a category list and drill into one
  category at a time (with a back link).
- **Difficulty descriptions** in the catalog, configurable via tag, so the
  numeric difficulty rating is explained in words.
- The catalog now respects the Student/Catalog deadline permission, so it can
  be opened and closed independently.
- Catalog sorting bug fixed (classes now sort by earliest section time).

PRs: `#4441 <https://github.com/learning-unlimited/ESP-Website/pull/4441>`_,
`#4948 <https://github.com/learning-unlimited/ESP-Website/pull/4948>`_,
`#4791 <https://github.com/learning-unlimited/ESP-Website/pull/4791>`_,
`#4537 <https://github.com/learning-unlimited/ESP-Website/pull/4537>`_

19. User search, permissions, and the user view page
-----------------------------------------------------

- **Permissions can be scoped by user filter.** A permission can now be
  granted to the subset of users matching a saved user-search filter, rather
  than to an entire user role — e.g. opening registration early to a specific
  cohort.
- **Equity outreach cohorts** are exposed as user lists from the registration
  profile module, for targeted outreach.
- **Inline AJAX editing of name and email** on the user view page.
- Common searches for user types that a program does not use are hidden, and
  combination queries in the user search controller were fixed.

PRs: `#4335 <https://github.com/learning-unlimited/ESP-Website/pull/4335>`_,
`#4090 <https://github.com/learning-unlimited/ESP-Website/pull/4090>`_,
`#4522 <https://github.com/learning-unlimited/ESP-Website/pull/4522>`_,
`#4205 <https://github.com/learning-unlimited/ESP-Website/pull/4205>`_,
`#4674 <https://github.com/learning-unlimited/ESP-Website/pull/4674>`_

20. Account and payment safety
-------------------------------

Changes admins should know about because they affect what users experience:

- **Password strength validation** is now enforced on registration and password
  change (Django's standard validators), so users will be rejected for weak
  passwords where previously they were not.
- Account activation tokens are now HMAC-signed rather than plaintext.
- The **Credit Card module can be made conditionally required** — required only
  when a student has an outstanding balance of at least $0.50 (program tag).
- Race conditions that allowed **over-enrolment** in class sections were fixed,
  and registration operations were wrapped in transactions.

PRs: `#5783 <https://github.com/learning-unlimited/ESP-Website/pull/5783>`_,
`#4747 <https://github.com/learning-unlimited/ESP-Website/pull/4747>`_,
`#4576 <https://github.com/learning-unlimited/ESP-Website/pull/4576>`_,
`#5225 <https://github.com/learning-unlimited/ESP-Website/pull/5225>`_,
`#5625 <https://github.com/learning-unlimited/ESP-Website/pull/5625>`_,
`#5410 <https://github.com/learning-unlimited/ESP-Website/pull/5410>`_

Also notable
============

Smaller items that may be worth a sentence in an announcement, but probably
not a whole one:

- **Active tags banner** — a banner shows when a program has non-default tags
  configured, so admins are not surprised by inherited settings.
  `#4670 <https://github.com/learning-unlimited/ESP-Website/pull/4670>`_,
  `#5377 <https://github.com/learning-unlimited/ESP-Website/pull/5377>`_
- **K-12 school database** — state/city fields, server-side autocomplete, a
  statistics form, and an NCES bulk import management command.
  `#4600 <https://github.com/learning-unlimited/ESP-Website/pull/4600>`_
- **Statistics page** — many bugs fixed (zip code stats, registration type
  filters, school filter, NULL graduation years, ``program_type`` errors) and
  substantially faster.
  `#4624 <https://github.com/learning-unlimited/ESP-Website/pull/4624>`_,
  `#4625 <https://github.com/learning-unlimited/ESP-Website/pull/4625>`_,
  `#4334 <https://github.com/learning-unlimited/ESP-Website/pull/4334>`_,
  `#5010 <https://github.com/learning-unlimited/ESP-Website/pull/5010>`_
- **Better error pages** — a unified base template, two tiers of information
  (user-friendly plus a details section), and a report button.
  `#4396 <https://github.com/learning-unlimited/ESP-Website/pull/4396>`_
- **OpenGraph and Twitter meta tags**, so links to the site preview properly
  when shared.
  `#4932 <https://github.com/learning-unlimited/ESP-Website/pull/4932>`_
- **AJAX scheduler toast notifications** instead of a text message log, and
  refactored tooltips.
  `#5902 <https://github.com/learning-unlimited/ESP-Website/pull/5902>`_,
  `#4618 <https://github.com/learning-unlimited/ESP-Website/pull/4618>`_
- **Moderation movement dependency loop diagnostic** in the scheduling checks,
  which detects unsatisfiable moderator movement chains.
  `#5073 <https://github.com/learning-unlimited/ESP-Website/pull/5073>`_
- **Custom forms modernized** — legacy jQuery removed, validation upgraded,
  plus assorted fixes (empty title validation, form-owner-only data access,
  default question ordering, labels).
  `#5869 <https://github.com/learning-unlimited/ESP-Website/pull/5869>`_,
  `#4753 <https://github.com/learning-unlimited/ESP-Website/pull/4753>`_,
  `#4583 <https://github.com/learning-unlimited/ESP-Website/pull/4583>`_,
  `#5956 <https://github.com/learning-unlimited/ESP-Website/pull/5956>`_
- **Teacher document upload suggestions** — previously uploaded documents are
  offered as suggestions on the class documents and bio pages, and teachers can
  remove their profile picture.
  `#4795 <https://github.com/learning-unlimited/ESP-Website/pull/4795>`_,
  `#4868 <https://github.com/learning-unlimited/ESP-Website/pull/4868>`_
- **Formstack medical module** now indicates whether the form has been
  completed.
  `#4099 <https://github.com/learning-unlimited/ESP-Website/pull/4099>`_
- **Resources** — a compulsory-timeslot checkbox on the resources page, and
  floating resources filtered by "returned" status.
  `#4514 <https://github.com/learning-unlimited/ESP-Website/pull/4514>`_,
  `#4211 <https://github.com/learning-unlimited/ESP-Website/pull/4211>`_
- **Volunteer registration** is now visually distinct from teacher
  registration.
  `#4667 <https://github.com/learning-unlimited/ESP-Website/pull/4667>`_
- **Deadline and registration date range validation** in program forms, plus
  validation of program max size and grade ranges.
  `#5748 <https://github.com/learning-unlimited/ESP-Website/pull/5748>`_,
  `#4965 <https://github.com/learning-unlimited/ESP-Website/pull/4965>`_

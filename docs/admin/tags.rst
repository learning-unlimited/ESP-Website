=======================
Customizing with Tags
=======================

.. contents:: :local:

Tags are the primary mechanism for enabling, disabling, or fine-tuning
optional behaviour on an ESP site — without any code changes.  This page is
the admin-facing guide.  For the developer-facing guide (declaring new tags in
code), see `dev/tags.rst <../dev/tags.rst>`_.

What Is a Tag?
==============

A **tag** is a named key–value pair stored in the database.  Think of it as a
configuration switch you can flip from the admin panel.  For example:

* Setting the tag ``volunteer_tshirt_options`` to ``True`` adds a T-shirt size
  field to the volunteer sign-up form.
* Setting ``group_phone_number`` to ``617-555-0100`` prints that number on
  nametags and room rosters.

Tags come in two flavors:

* **Global tags** — apply site-wide, across all programs.
  Navigate to ``https://[yoursite].learningu.org/manage/tags/`` for global
  tag settings.
* **Program tags** — apply to one specific program only.
  Navigate to ``https://[yoursite].learningu.org/manage/<program>/tags/``
  for a specific program. The program-level value takes precedence over the
  global default for that program only.

Both pages show all tags that are marked as user-facing settings, grouped
by category, with help text for each one.

How to Set a Tag
================

1. Go to the Tag Settings page.
2. Find the tag you want — each entry shows a description.
3. Enter the desired value and save.

Tag Categories
==============

Tags are grouped into the following categories on the Tag Settings page:

* **teach** — settings that affect teacher registration and class creation.
* **class** — settings that affect individual classes (e.g., scheduling and
  display).
* **learn** — settings that affect student registration and the course catalog.
* **manage** — site-management settings (names, contact info, etc.).
* **onsite** — settings relevant during the day of the event.
* **volunteer** — settings for the volunteer sign-up form.
* **moderate** — settings related to moderating or approving content and
  activity.
* **theme** — settings related to the visual theme.



ClassRegModuleInfo (CRMI) and StudentClassRegModuleInfo (SCRMI)
===============================================================

For settings that control the registration module behaviour (grade limits,
lottery mode, teacher deadlines, etc.) see the dedicated admin forms:

* **CRMI** (teacher-facing class registration):
  ``/admin/modules/classregmoduleinfo/``
* **SCRMI** (student-facing class registration):
  ``/admin/modules/studentclassregmoduleinfo/``

A full description of every field for both forms is in
`admin/program_modules.rst <program_modules.rst>`_.

See Also
========

* Developer guide to declaring and reading tags in code:
  `dev/tags.rst <../dev/tags.rst>`_
* Program modules and SCRMI/CRMI fields reference:
  `admin/program_modules.rst <program_modules.rst>`_
* Customization index: `customizing.rst <../customizing.rst>`_

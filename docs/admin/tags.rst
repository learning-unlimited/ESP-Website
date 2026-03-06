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

Tags come in two flavours:

* **Global tags** — apply site-wide, across all programs.
* **Program tags** — apply to one specific program only.

Where to Find Tags
==================

There are two ways to access tags:

1. **Tag Settings page** (recommended for common settings):

   Navigate to ``https://[yoursite].learningu.org/​manage/tag_settings/``.
   This page shows all tags that are marked as user-facing settings, grouped
   by category, with help text for each one.  You only see the tags that are
   safe to adjust through the settings UI.

2. **Django admin** (for advanced / raw access):

   Navigate to ``https://[yoursite].learningu.org/admin/tagdict/tag/``.
   This shows every tag in the database and lets you create, edit, or delete
   them directly.  Use this for tags that are not shown on the Tag Settings
   page, or when you need to associate a tag with a specific program.

How to Set a Tag
================

**Global tag (applies to all programs):**

1. Go to the Tag Settings page (or Django admin ``/admin/tagdict/tag/``).
2. Find the tag you want — each entry shows a description.
3. Enter the desired value and save.
4. Leave *Content Type* and *Object ID* blank for a global tag.

**Program-specific tag (overrides globally for one program):**

1. Go to ``/admin/tagdict/tag/add/``.
2. Enter the tag key (e.g. ``open_class_category``).
3. Enter the value.
4. Under *Content Type*, choose **Program**; under *Object ID*, enter the
   numeric ID of your program (visible in the program's admin URL).
5. Save.  The program-level value takes precedence over the global default for
   that program only.

Tag Categories
==============

Tags are grouped into the following categories on the Tag Settings page:

* **teach** — settings that affect teacher registration and class creation.
* **learn** — settings that affect student registration and the course catalog.
* **manage** — site-management settings (names, contact info, etc.).
* **onsite** — settings relevant during the day of the event.
* **volunteer** — settings for the volunteer sign-up form.
* **theme** — settings related to the visual theme.

Common Tags Reference
=====================

The table below lists frequently used tags.  The full list of available tags
(with help text) is on your site's Tag Settings page.

.. note::
   Boolean tags should be set to ``True`` to enable the feature and left
   unset (or deleted) to use the default (usually disabled) behaviour.

Site-wide (manage)
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Tag key
     - Type
     - What it does
   * - ``full_group_name``
     - string
     - Official name of the group, used where a formal name is required beyond
       ``INSTITUTION_NAME`` / ``ORGANIZATION_SHORT_NAME`` settings.
   * - ``group_phone_number``
     - string
     - Phone number printed on nametags and room rosters.

Teaching (teach)
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Tag key
     - Type
     - What it does
   * - ``use_class_size_optimal``
     - boolean
     - Ask teachers for an *optimal* class size instead of maximum size.
   * - ``nearly_full_threshold``
     - decimal
     - Fraction (0.0–1.0) of section capacity at which a class is shown as
       "nearly full" (default: 0.75).
   * - ``allow_global_restypes``
     - boolean
     - Show global resource types in manage-resources and teacher registration
       options.
   * - ``min_available_timeslots``
     - integer
     - Minimum number of timeslots teachers must mark available before they can
       register a class.
   * - ``teacherreg_custom_forms``
     - JSON
     - JSON list of custom form names to add to the teacher class-registration
       form.

Student / Learning (learn)
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Tag key
     - Type
     - What it does
   * - ``increment_default_grade_levels``
     - boolean
     - Treat all students as one grade higher (useful for summer programs where
       students have just finished a grade).
   * - ``open_class_category``
     - integer
     - Category ID used for open classes (no advance registration).
   * - ``catalog_sort_fields``
     - string
     - Comma-separated list of fields to sort the course catalog by.

Volunteer (volunteer)
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Tag key
     - Type
     - What it does
   * - ``volunteer_tshirt_options``
     - boolean
     - Add T-shirt size and type fields to the volunteer form.
   * - ``volunteer_shirt_sizes``
     - string
     - Comma-separated list of shirt-size options for volunteers
       (default: XS, S, M, L, XL, XXL).
   * - ``volunteer_allow_comments``
     - boolean
     - Add a free-text comments field to the volunteer form.

Theme (theme)
-------------

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Tag key
     - Type
     - What it does
   * - ``fruitsalad_sounds``
     - boolean
     - Enable Easter-egg sounds in the Fruitsalad theme.

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

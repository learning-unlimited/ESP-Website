============================
Customizing the ESP Website
============================

.. contents:: :local:

This page is a **starting point** for anyone who wants to change how the ESP
website looks or behaves.  It lists every major customization mechanism, gives
a short description of each, and links to the relevant detailed documentation.
Pick the section that matches what you want to do.

QSD — Inline Text Blocks
=========================

*Audience: site admins*

QSD ("Quasi-Static Data") lets admins edit pieces of text or images that are
embedded directly inside existing pages — without touching any code.  For
example, the introductory paragraph on a program splash page is typically a
QSD block.  Any page that contains a ``render_inline_qsd`` or
``inline_qsd_block`` template tag exposes an editable region to admins.

* Developer reference (template tags ``render_inline_qsd``,
  ``inline_qsd_block``, and their program-scoped variants):
  `dev/utils.rst <dev/utils.rst>`_

QSD — Standalone Pages
=======================

*Audience: site admins*

Admins can also create entirely new content pages served at
``/Q/<page-name>/``.  These pages are managed through the admin toolbar
("Edit this page") on the live site, or via the Django admin interface.

* Developer reference (same rendering machinery): `dev/utils.rst <dev/utils.rst>`_

Tags and (S)CRMI
================

*Audience: site admins and developers*

**Tags** are key–value settings (global or per-program) that control optional
site behaviour — for example, enabling a custom registration workflow or
setting a program-specific reply-to e-mail address.  Tags are visible to
chapter admins on the tag settings page under the admin toolbar.

**StudentClassRegModuleInfo (SCRMI)** and **ClassRegModuleInfo (CRMI)** are
database objects that expose per-program configuration knobs for the class
registration modules (e.g. grade limits, lottery behaviour, teacher deadlines).

* Admin guide (how to set tags from the admin panel): `admin/tags.rst <admin/tags.rst>`_
* How to declare and use Tags (developer guide): `dev/tags.rst <dev/tags.rst>`_
* SCRMI / CRMI fields reference: `admin/program_modules.rst <admin/program_modules.rst>`_
* Background on documenting tags: `GitHub issue #2038
  <https://github.com/learning-unlimited/ESP-Website/issues/2038>`_

Themes and Visual Customizations
=================================

*Audience: site admins*

The ``/themes/`` app lets admins pick a pre-built layout, fill in
site-specific information (title, contact details, navigation links), and
adjust the colour palette and logo — all through a web form, with no code
changes required.  There are three steps: *Select* a theme, *Set up* the
theme, and *Customize* the theme.

* Admin guide (select → set up → customize): `admin/themes.rst <admin/themes.rst>`_
* Catalogue of available themes with screenshots:
  `admin/available_themes.rst <admin/available_themes.rst>`_

Template Overrides
==================

*Audience: advanced admins and developers*

Any Django template can be overridden for a specific site by saving a new
version to the database via the ``TemplateOverride`` model.  The themes app
uses this mechanism internally; it is also useful for customising printables
and other one-off pages.

.. note::
   Loading a theme will overwrite your existing template overrides, so keep
   copies of any manual overrides before experimenting with the themes app.

* Model description and usage: `dev/utils.rst <dev/utils.rst>`_
* Manual theming workflow (without the app): `admin/themes.rst <admin/themes.rst>`_
  — see the *Manual Theming* section.

Custom Themes / Adding a New Theme
====================================

*Audience: developers*

To contribute a fully custom front-end design for other chapters to use,
package it as a theme inside ``esp/themes/theme_data/``.  The themes app
compiles LESS → CSS with user-supplied parameters at runtime.  A theme
consists of pre-defined template overrides, images, and LESS stylesheets.

* Full developer guide (architecture, file layout, LESS pipeline, adding a
  theme): `dev/themes.rst <dev/themes.rst>`_

Contributing to the Codebase
==============================

*Audience: developers*

For changes that go beyond configuration — new features, bug fixes, or
structural improvements — follow the standard development workflow: fork the
repository, work on a feature branch, write tests, open a pull request, and
go through code review.

* Git workflow and PR process: `dev/contributing.rst <dev/contributing.rst>`_
* Background on code-review guidelines: `GitHub issue #1660
  <https://github.com/learning-unlimited/ESP-Website/issues/1660>`_

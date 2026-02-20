Django Cotton Evaluation (Issue #3916)
======================================

Goal
----

Evaluate ``django-cotton`` for component-based template design and determine whether
it is a good fit for this codebase now.


Current template organization (quick audit)
-------------------------------------------

The codebase currently uses classic Django template composition:

* ``{% extends %}`` for page shells and theme inheritance.
* ``{% include %}`` for reusable fragments (navbar sections, login fragments, module subviews).
* Context-driven rendering from Python views and module handlers.

Observed pattern in this repo:

* High include density in ``esp/templates/program/modules/*`` and themed ``main.html`` files.
* Shared fragments are reusable, but composition is limited to include/with conventions.
* Slots and attribute-style composition are not available in native DTL includes.


Prototype component
-------------------

A prototype reusable component was added at:

* ``esp/templates/cotton/prototypes/nav_dropdown.html``

This prototype mirrors a recurring dropdown menu pattern seen in login/navbar
fragments and demonstrates Cotton-style component attributes with looped link
data.

Prototype usage example (Cotton syntax):

.. code-block:: html

   <c-prototypes.nav-dropdown
       :links="[
         {'href': '/myesp/accountmanage/', 'label': 'Manage Account'},
         {'href': '/myesp/loginhelp.html', 'label': 'Help'},
         {'href': 'https://www.learningu.org/about/privacy/', 'label': 'Privacy Policy', 'target': '_blank'}
       ]"
   />

Comparable existing approach today uses repeated markup blocks and ``{% include %}``
with limited parameterization.


Integration steps (if adopted)
------------------------------

1. Add dependency:

   * ``django-cotton`` in ``esp/requirements.txt``

2. Add app in settings:

   * ``'django_cotton'`` in ``INSTALLED_APPS``

3. Ensure template loader setup is compatible with Cotton docs if custom loaders
   are in use.

4. Create components under:

   * ``esp/templates/cotton/``

5. Incrementally migrate repeated UI fragments (alerts, nav items, CTA blocks,
   form rows) and keep behavior parity tests around high-risk pages.


Limitations / risks for this repository
---------------------------------------

Major blocker for immediate adoption:

* Current stack is ``Django==2.2.28`` (see ``esp/requirements.txt``).
* Upstream ``django-cotton`` currently documents support for Django 4.2+ and
  Python 3.8+.

Implications:

* Immediate adoption would require a broader framework/runtime upgrade first.
* Attempting to force-install Cotton into this stack is high risk and not
  suitable for a small feature PR.


Recommendation
--------------

**Recommendation: defer adoption for now.**

Short-term:

* Keep using current ``extends/include`` patterns.
* Optionally introduce local include conventions for common fragment APIs.

Medium-term (after Django/Python upgrade):

* Re-open this spike and run a focused pilot on 2-3 repeated fragments.
* If pilot succeeds, define component conventions and migration guidelines.

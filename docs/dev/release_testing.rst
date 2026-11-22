Release testing: URL inventory and browser crawl
================================================

Before a release, two tools help make sure every page gets looked at:

- ``manage.py url_inventory`` lists every page on the site, who should be able
  to see it, and whether the crawl can visit it safely. Its CSV works as a
  manual testing checklist.
- ``deploy/release_testing/crawl.py`` visits every safe page in that list as each
  role (anonymous, student, teacher, volunteer, onsite, admin) in a real browser.
  It reports server errors, pages a role should or shouldn't have reached,
  JavaScript errors, broken assets, and a screenshot of each page.

The crawl complements ``testAllViews`` (``esp/program/modules/tests/testallviews.py``),
which checks every program module view as an admin through Django's test
client. The crawl adds the other roles, the non-module pages and QSD pages,
JavaScript and asset errors, and can run against a copy of real chapter data.

.. warning::

   Only crawl a **disposable copy** of a site, never a live one. The crawl
   sends only GET requests and skips views that look like they change data,
   but both checks are heuristics. ``crawl_sessions`` writes to the database
   and its output file holds working login tokens.

What the inventory contains
---------------------------

One row per URL (or URL pattern), from three sources:

- the Django URLconf, including the Django admin site;
- every ``@main_call`` / ``@aux_call`` view of every program module, with a real
  URL for each program passed with ``--program`` (default: the newest program);
- QSD pages stored in the database.

Useful columns:

``expected_roles``
    Roles the view's access decorators let through (``needs_admin``,
    ``needs_student_in_grade``, ``login_required`` and so on). Blank when access
    is decided by custom code such as ``user_passes_test``.
``crawlable`` / ``skip_reason``
    Whether the crawl visits the URL, and why not. Rows are skipped when the URL
    needs arguments (e.g. a class ID), the view only accepts POST, the view's
    name suggests it changes data (``delete``, ``signout``, ``checkin``...), or
    ``writes_on_get`` is set. A ``skip_reason`` of "no access decorator found"
    on a crawlable row means the view may still check access in its body.
``writes_on_get``
    Calls in the view that look like database writes (``.save()``,
    ``.delete()``, ``objects.create()``...) and aren't behind a POST check.
    This reads only the view's own code, not the functions it calls. If a
    flagged write is harmless, add the view to ``GET_WRITES_REVIEWED`` in
    ``esp/utils/url_inventory.py`` with the reason, so the crawl visits it.
``kind``
    ``endpoint`` for AJAX/JSON views, which usually need query parameters.
``source``
    File and line of the view.

Every row with ``crawlable = no`` needs a manual check if it matters for the
release. Filter the CSV on that column to build the manual checklist.

Running a crawl
---------------

1. Restore a copy of a chapter's database (or seed a dev database with
   ``./manage.py seed_dummy_data``) and run the release's migrations on it.
   Start the site. On a fresh dev site, load a theme first (e.g. from
   ``/themes/``) or every page will report a missing ``theme_compiled.css``.

2. Write the inventory::

     cd esp
     ./manage.py url_inventory --program Splash/2026 --out-dir /tmp/crawl

3. Create login sessions, one user per role::

     ./manage.py crawl_sessions --program Splash/2026 --out /tmp/crawl/sessions.json

   For each role it picks an active user, preferring one involved in the
   program (a teacher of one of its classes, an enrolled student...) and never
   an admin for the non-admin roles. Choose users yourself with
   ``--user teacher=jdoe``. ``--create-missing`` creates ``crawl_<role>`` users
   for roles with no suitable user. Sessions last 4 hours (``--hours``).

4. Install Playwright (only needed for the crawl, not the site)::

     pip install -r deploy/release_testing/requirements.txt
     playwright install chromium

5. Crawl::

     python deploy/release_testing/crawl.py \
         --inventory /tmp/crawl/inventory.json \
         --sessions /tmp/crawl/sessions.json \
         --base-url http://localhost:8000 \
         --out /tmp/crawl/results

   A site that isn't on ``localhost`` also needs ``--target-is-disposable``.
   ``--area learn --area teach`` or ``--url-regex`` narrow the crawl, and
   ``--limit 20`` makes a quick trial run. ``--help`` lists the rest.

   On a seeded dev database with ``manage.py runserver``, 525 URLs as six
   roles (about 3,150 visits) took about 16 minutes at ``--concurrency 6``.
   A copy of a large chapter will have more QSD pages and take longer.

   Each visit is saved to ``progress.jsonl`` in the output directory as it
   finishes. If the crawl is interrupted, run the same command with
   ``--resume`` to skip the visits already done.

6. Open ``/tmp/crawl/results/report.html``. Then revoke the sessions::

     ./manage.py crawl_sessions --revoke /tmp/crawl/sessions.json

Comparing two versions
~~~~~~~~~~~~~~~~~~~~~~

Crawl the current release and the release candidate on copies of the same
database, then pass the first run's ``results.json`` to the second with
``--compare``. The report then lists every page whose outcome, status code or
verdict changed, plus pages that appeared or disappeared, and ``changes.csv``
holds the same list. Use the inventory from the newer code for both runs.

Reading the report
------------------

Each (URL, role) visit gets one verdict, most serious first:

``server-error``
    HTTP 5xx, or the page didn't load. A page that keeps navigating after it
    loads (a redirect loop) also ends up here, with the URLs it visited.
``unexpected-allow``
    The role got the page, but its access decorators say it shouldn't have.
    Check these first: they can be security problems.
``not-found``
    HTTP 404 for a role that should see the page.
``unexpected-deny``
    A role that should see the page was refused or sent to log in. Often a
    deadline or setting of the program rather than a bug, and expected for
    views with no access decorator that check access in their body.
``endpoint-error``
    An AJAX/JSON endpoint returned 5xx to a GET without its parameters. It
    should answer 400 instead, but this is lower priority than a broken page.
``js-error`` / ``asset-error``
    The page loaded but logged JavaScript errors, or a script, stylesheet,
    image or font failed to load.
``closed``
    A deadline, grade or capacity page. Check the program's setup.
``needs-input``
    HTTP 400 or 405, or ESP's "Your request could not be processed" page
    (``ESPError(log=False)``, which is sent as HTTP 500): the view wants
    parameters such as a class ID, or a POST. Low priority, but each one
    should get a manual check with real input.
``ok`` / ``info``
    Loaded as expected (``info``: access is custom, so nothing to compare).

The crawl recognises ESP's "access denied" and "deadline closed" pages by
their text. A chapter's template overrides can change that text, in which case
those pages show up as ``ok`` or ``unexpected-allow``.

The crawl exits with status 1 when there are ``server-error`` or
``unexpected-allow`` results, so it can run in CI.

Limitations
-----------

- Only GET requests with no parameters: no forms are submitted, and views
  that need an ID in the URL are listed but not visited.
- Expected roles come from decorators, not from running the access checks.
- Screenshots are for skimming; they are not compared between runs.

The crawler's own tests run without Django::

  python -m pytest deploy/release_testing

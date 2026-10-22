# AGENTS.md

Guidance for AI coding agents (and the people driving them) working on the ESP Website. It covers the mistakes that most often get pull requests sent back. For everything else, follow the human docs:

- Dev setup: [`docs/dev/docker.rst`](docs/dev/docker.rst)
- Workflow, tests and reviews: [`docs/dev/contributing.rst`](docs/dev/contributing.rst), [`docs/dev/testing.rst`](docs/dev/testing.rst)
- Subsystems: [`docs/dev/`](docs/dev/) (program modules, tags, caching, themes, email)

## Project at a glance

A Django 5.2 site on Python 3.12, backed by PostgreSQL and memcached, used by Learning Unlimited chapters to run educational programs for students, many of them minors. Treat user data and access control accordingly.

| Path | What lives there |
| --- | --- |
| `esp/esp/<app>/` | Django apps: `program`, `users`, `customforms`, `tagdict`, `themes`, `accounting`, ... |
| `esp/esp/program/modules/handlers/` | Program module views (registration, scheduling, management) |
| `esp/esp/program/modules/base.py` | Module base class and access-control decorators |
| `esp/templates/` | Django templates |
| `esp/esp/themes/theme_data/<theme>/scss/` | Theme stylesheets |
| `docs/admin/releases/upcoming/README.rst` | Release notes for the next release |
| `deploy/ci/` | Scripts that CI runs |

## Before you say a change is done

Run these yourself; do not rely on CI to find problems. With Docker (see `docs/dev/contributing.rst`), prefix commands with `docker compose exec -w /app/esp web`. Paths are relative to `esp/`.

```bash
pytest esp/<app>/tests.py           # or a tests/ dir, or -k <name>
pytest --create-db                  # once, after any migration change
python manage.py check
python manage.py makemigrations --check --dry-run
```

Lint from the repository root with `deploy/lint` (flake8; Python only).

Some tests fail only because local tools such as `pdflatex`, ghostscript or sass are missing. Compare against the same tests on `main` before treating a failure as yours.

## Passing CI is not proof the change works

- **Show your test can fail.** Run new tests against the unpatched code and confirm they fail. A test that also passes on `main` proves nothing.
- **Exercise the real path.** `Model.objects.create()` skips form and choice validation, so a test built that way can pass while the admin or form path is broken. Test through the form or view when that is what users touch.
- **Look at the page.** If you change a template, view, JS or CSS, load the page and use the feature. CI only lints Python; JavaScript syntax errors and hidden or unstyled elements will not fail it.
- **Fork PRs may not run CI** until a maintainer approves the workflow, and PRs with merge conflicts do not run it at all. Your own local run is the only check until then.

## Codebase rules and traps

**Django and Python**
- Target Django 5.2. Do not use APIs removed in Django 4.x/5.x (for example `django.utils.http.is_safe_url` or `django.contrib.postgres.fields.JSONField`); they stop the whole site from starting. Check the Django 5.2 docs when unsure.
- No bare `except:` or `except Exception: pass`. Silent excepts have hidden broken features for years, and swallowing a database error inside `transaction.atomic()` leaves the transaction unusable.

**Templates**
- All templates use the Django template engine, not Jinja2. Jinja-only filters and syntax (for example `|trim`) raise `TemplateSyntaxError` on every page that includes the template.

**Styles and front end**
- Themed pages use Bootstrap 5. Do not add Bootstrap 2/3 markup or classes.
- Theme styles are SCSS under `esp/esp/themes/theme_data/<theme>/scss/`. The old LESS theme sources are gone; the `.less` names in `esp/esp/themes/controllers.py` are a legacy storage format for saved customizations, not stylesheets to edit.
- There are six themes (`barebones`, `bigpicture`, `circles`, `droplets`, `floaty`, `fruitsalad`). Check visual changes in more than the default one.
- Do not reformat whole files (Prettier, Black, etc.). Change only the lines your fix needs.

**Migrations**
- Branch from current `main`. If another migration with your number landed first, renumber yours so there is a single leaf; `makemigrations --check` must be clean.
- New fields, permissions or defaults that existing programs rely on usually need a data (backfill) migration, not just a default for newly created rows.
- Data migrations must handle large tables: use `iterator()` and `bulk_update()` rather than loading and saving rows one by one, and make the reverse migration safe.

**Transactions**
- `ATOMIC_REQUESTS = True` in `esp/esp/django_settings.py` has no effect (Django only reads it inside a `DATABASES` entry). Requests are not wrapped in a transaction, so wrap multi-step writes in `transaction.atomic()` yourself. `select_for_update()` must run inside one.

**Access control**
- `@needs_teacher`, `@needs_student` and similar decorators in `esp/esp/program/modules/base.py` only check the user's role. They do not check that the user may act on this program, class or section. Add an object-level check (for example, that the teacher teaches the section) for anything that reads or changes someone else's data.
- A security fix must keep the site working: do not delete helpers that are still called, and do not change login, redirect or registration flows without tests for the normal path as well as the attack.

**Caching and performance**
- Many functions are cached with django-argcache; read [`docs/dev/cache.rst`](docs/dev/cache.rst) before changing cached code or the models it depends on. Never cache output that depends on the current user or their timezone under a key that does not include them.
- Avoid N+1 queries on list pages (catalog, dashboards, statistics). Use `select_related` / `prefetch_related`, and pin the result with `assertNumQueries` in a test.

**Tags (site settings)**
- Settings live in `tagdict`; see [`docs/dev/tags.rst`](docs/dev/tags.rst). Define new tags in `all_global_tags` or `all_program_tags` in `esp/esp/tagdict/__init__.py`, and keep existing tag values working after a change.

## Pull requests

- **Confirm the issue still exists on `main`** before writing code. Some issues have already been fixed, and some describe behavior that cannot happen.
- **One issue per PR**, branched from up-to-date `main`. If your branch falls behind, merge `main` into it and resolve conflicts carefully: stale branches have silently undone merged work.
- **Keep scope tight.** No unrelated refactors, renames or formatting.
- **Fill in the PR template**, including the **AI Disclosure** section, and link the issue (`Closes #123`).
- **Add a release note** to `docs/admin/releases/upcoming/README.rst` for user-facing changes.
- **Review comments, including Copilot's, are resolved by changing the code** or by replying with why no change is needed. Do not mark a thread resolved without one of these.
- **Say what you ran.** In the PR's Testing section, list the commands you ran and their results, and say what you checked by hand.

## Security

Report vulnerabilities privately by email as described in [`SECURITY.md`](SECURITY.md). Do not describe an unpatched vulnerability in a public issue, PR title, PR body or commit message.

## Ask a maintainer first

- Changes to `deploy/`, `.github/workflows/`, `Dockerfile` or `docker-compose.yml`
- New dependencies in `esp/requirements.txt`
- Editing `esp/.test_durations` (generated timing data used to split CI test shards)
- Removing or renaming a feature, model field or tag that chapters may use

Never commit `esp/esp/local_settings.py`, credentials or real user data.

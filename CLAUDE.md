# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Rules

**DO NOT run website code, tests, linting, or dependency scripts.** This means no `manage.py` commands, no `deploy/lint`, no `update_deps.sh`, etc. The user runs these themselves.

**Git and git-imerge commands are fine to run**, including `git-imerge continue`, `git add`, `git commit`, `git show`, `git log`, `git diff`, etc.

**During merge resolution: if there is ANY controversy or uncertainty about intent, ASK the user before making changes.** Only accept changes that are clearly uncontroversial — minor correct refactors, no functional change, or minor bug fixes with no real external impact. When in doubt, ask.

**For formatting-only conflicts, always take the LU version.** If the only difference between HEAD and LU is indentation, whitespace, line wrapping, or trailing spaces — with no functional change — take LU's version without asking.

## Project Overview

Django 1.11 / Python 2.7 web application for MIT Educational Studies Program (ESP), managing logistics of large short-term educational programs (e.g. Splash). Originally developed at MIT, now maintained upstream by Learning Unlimited (LU). This repository is the MIT fork, currently being updated to absorb LU stable-release-14 on top of the prior stable-release-13 merge.

**Branch structure:**
- `BIG_MERGE_MIT` — result of stable-release-13 merge (via `git-imerge`) plus post-merge bug fixes
- `merge_sr14` — working branch for stable-release-14 merge (built on top of `BIG_MERGE_MIT`)

## Commands Reference (for the user to run)

```bash
# Tests
cd esp && python manage.py test                     # all tests
cd esp && python manage.py test esp.program         # single app tests

# Lint
deploy/lint                                         # flake8 with limited checks

# Dev server
cd esp && python manage.py runserver 0.0.0.0:8000
# Or via Fabric (runs inside Vagrant VM):
fab runserver

# Database
fab loaddb                                          # load encrypted db dump from /mnt/encrypted/fabric/dbdump
fab dumpdb                                          # dump db to devsite_django.sql

# Dependencies
esp/update_deps.sh                                  # system + Python packages

# Static files
cd esp && python manage.py collectstatic --noinput
```

Lint checks: mixed tabs/spaces, undefined names, duplicate arguments, tab indentation, trailing whitespace, deprecated Python 2 constructs (`has_key`, `<>`, backticks).

## Architecture

### Django Project Layout

- `esp/manage.py` — Django entry point
- `esp/esp/` — main package (`DJANGO_SETTINGS_MODULE=esp.settings`)
- `esp/templates/` — all templates, organized by app
- `esp/public/media/` — static assets (JS, CSS, images), served at `/media/`

### Settings Chain

1. `esp/esp/django_settings.py` — shared defaults; do not modify directly
2. `esp/esp/local_settings.py` — site-specific overrides; not in repo, generated from `deploy/config_templates/`
3. `esp/esp/settings.py` — imports both above, computes derived settings

### Core Apps

| App | Purpose |
|-----|---------|
| `program` | Programs, ClassSubjects, ClassSections, the module system |
| `users` | ESPUser, Permissions, Records, ContactInfo |
| `resources` | Rooms and resources used by programs |
| `qsd` | Admin-editable text pages (Quick Static Documents) |
| `dbmail` | Email system with custom SMTP backend |
| `customforms` | Dynamic form builder |
| `themes` | Theming engine |
| `utils` | Shared utilities, custom auth backend, caching |
| `tagdict` | Tag-based configuration system |

### Program Module System

The primary extensibility pattern. Modules are per-program optional features (teacher checkin, credit card payments, lottery, etc.).

- Base class: `esp/esp/program/modules/base.py`
- Implementations: `esp/esp/program/modules/handlers/` (~30+ handler files)
- Module metadata models: `esp/esp/program/modules/models.py`
- Docs: `docs/dev/program_modules.rst`

### URL Routing

Dynamic dispatch in `esp/esp/urls.py`. Program-facing URLs follow:
```
/(onsite|manage|teach|learn|volunteer|json)/<ProgramType>/<ProgramInstance>/<ModuleName>/
```

### Infrastructure

- **Database:** PostgreSQL via psycopg2
- **Cache:** Memcached at `127.0.0.1:11211` via custom `esp.utils.memcached_multikey.CacheClass`
- **Dev environment:** Vagrant VM (Ubuntu 20.04), Fabric commands (`fab runserver`, `fab loaddb`, etc.)

## Merge Process

### Starting / Continuing the sr14 imerge

```bash
# Initialize a new imerge (if not yet started):
git imerge start --name=BIG_MERGE_MIT_SR14 --onto=merge_sr14 stable-release-14

# Fetch imerge state from remote (if resuming):
git fetch --prune origin +refs/imerge/<BRANCH>/*:refs/imerge/<BRANCH>/*

# Push imerge state + final branch
git push --prune origin +refs/imerge/<BRANCH>/*:refs/imerge/<BRANCH>/*
git push origin +<BRANCH>

git-imerge continue
```

### Workflow Rules

- Run `git add`, `git commit --no-edit`, and `git-imerge continue` as **separate Bash calls**, not chained with `&&`. This way if the commit fails (e.g. linter hook), you see the error clearly.
- **Do NOT run `git-imerge finish`** — the user handles that step (and the subsequent push).
- When `git-imerge continue` reports "Merge is complete!", stop and tell the user.
- `grep -c "<<<<<<" file` returns exit code 1 when count is 0, which breaks `&&` chains. Use `|| true` or check separately.

Resolve conflicts conservatively — preserve MIT behavior unless the LU change is clearly a bug fix or improvement with no ambiguity.

### Edit Tool Gotcha: Tabs vs Spaces in Conflict Markers

The Edit tool requires exact byte matching. Conflict markers sometimes contain tab characters in the HEAD section (mixed with spaces), causing "String to replace not found" even when the content looks identical. If Edit fails unexpectedly:
1. Run `sed -n 'START,ENDp' FILE | cat -A` to inspect exact bytes (`^I` = tab, `$` = line end).
2. If the conflict region is all-spaces, Edit tool works fine.
3. If it's mixed tabs/spaces, use perl: `perl -i -0pe 's/\Q<<<<<<< HEAD\E.*?\Q>>>>>>> HASH\E\n/REPLACEMENT/s' FILE`

### Linter Hook Behavior

The linter runs as a git pre-commit hook after each `git commit`. It sometimes **reverts files** to earlier states when it detects issues (notably in `Matrix.js` where it oscillates the HSSP/Splark formula between versions). If a file looks wrong after a commit, check whether the linter hook modified it.

## MIT Terminology and Configuration

MIT uses "**observer**" for what LU calls "**moderator**" — same functionality, different name. The `moderator_title` tag defaults to `'Observer'` in this repo (set in `esp/esp/tagdict/__init__.py`); LU's default is `'Moderator'`. Keep the MIT default.

## MIT-Specific Features to Preserve

These are MIT additions that are NOT in LU upstream and must be kept through merges:

- **`lottery.py`**: `section_filledness` computation, `chart_constructor` method, `extract_chart_stats` method — MIT's lottery frontend charts feature.
- **`studentregphasezero.py`**: Three separate email methods (`send_joingroup_confirmation_email`, `send_other_joined_group_confirmation_email`, `send_leavegroup_confirmation_email`) rather than LU's single `send_confirmation_email`. MIT callers depend on all three.
- **`studentregcore.py`**: `q_studentrep` is intentionally commented out (MIT choice).
- **`teacherpreviewmodule.py`**: `"choosable": 0` is intentional (MIT doesn't want this module user-selectable).
- **`update_deps.sh`**: Python 2.7.18 built-from-source hack — harmless on Ubuntu 20 (version check passes immediately), keep it.
- **Schedule templates**: MIT adds "ET" timezone label to time cells (`{{ cls.time_blocks.0.short_time }} ET`).
- **`bigboard_graph.html`**: Use `axis.first_hour` (per-axis value from backend context), NOT `first_hour` (LU's global variable that doesn't exist in the backend).
- **`tagdict/__init__.py`**: `moderator_title` default is `'Observer'` (MIT), not `'Moderator'` (LU).
- **`class_teacher_list_row.html`**: LU's sr14 restructured this into Bootstrap dropdowns. MIT resolution: comment out the "Request Cancellation" link (entire `{% if can_req_cancel %}` block), keep "Email Students" (it's in LU's student dropdown), keep section visibility as `{% if not cls.isRejected %}` (not `isAccepted`).

### Observer → Moderator Migration (already applied)

The data migration `program/migrations/0026_copy_observers_to_moderators.py` already copies the MIT `classsection_observers` M2M table into LU's `classsection_moderators`. This is complete; no further data migration is needed.

### Customforms Migration (already applied)

`customforms/migrations/0003_fix_checkbox_correct_answer_separator.py` fixes two data issues introduced by LU's sr13 changes to `DynamicForm.py`:
- Strips trailing `|` from stored options (options were stored with a trailing pipe that the new code doesn't strip)
- Converts checkbox `correct_answer` separators from `,` to `|` (LU changed the separator)

## Recurring Conflict Patterns and Established Resolutions

These files have conflicted repeatedly. Use these resolutions unless the new LU commit changes the conflict meaningfully:

**`esp/make_virtualenv.sh`**
- MIT uses `python -m pip install "virtualenv>=1.10"` and `python -m virtualenv "$VENVDIR"`.
- LU uses bare `pip2` / `virtualenv`. Keep MIT's `python -m` form (more robust inside virtualenvs).
- Do NOT use `sudo -u www-data virtualenv` — LU itself reverted this (commit `7fc639a36`) because www-data lacks write permission.

**`esp/packages_base_manual_install.sh`**
- Resolution: Ubuntu version-conditional `apt` vs `apt-get` for Node.js LTS install. Keep both `curl` and `python-software-properties`. Pattern:
  ```bash
  if [ $(echo "$(lsb_release -rs) >= 20" | bc) -eq 1 ]; then
    sudo apt install -y curl
  else
    sudo apt-get install -y curl
  fi
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  # ... similar pattern for nodejs
  ```

**`esp/update_deps.sh`**
- Keep LU's `get-pip.py` bootstrap step (genuine bug fix: pip must be installed before virtualenv).
- Keep MIT's `python -m pip` for all subsequent installs (not bare `pip`).
- Keep `apt-get` (not `apt`) for backwards compat with Ubuntu 14.

**`esp/public/media/scripts/ajaxschedulingmodule/ESP/Matrix.js`**
- LU repeatedly inserts `addClassToSections` function before `var available_timeslots`.
- HEAD's conflicting code is a duplicate already present in the non-conflicted area below.
- Resolution: Always take LU's `addClassToSections` insertion, drop HEAD's duplicate.

**`esp/esp/program/modules/handlers/teacherbigboardmodule.py`**
- Conflict in `reg_classes`, `style_classes`, `teach_times` methods.
- Resolution: LU's formatting + `scheduled` param + module-level `get_filter` function; keep `self` for instance methods; `style_classes = staticmethod(style_classes)`.

**`esp/templates/program/modules/teacheronsite/schedule.html`**
- LU adds moderator title display. MIT has "(Observer)" label. Taking LU's version combines both. Keep MIT's "ET" time label.

## One-Time Decisions (for reference)

- `status__gte=0` (MIT) is correct for teacher mailing list removal: remove teacher only when ALL their classes are rejected/cancelled (status < 0). LU's `status__gte=10` was incorrect — it would remove teachers who still have unreviewed classes.
- `numpy.bool_` instead of `numpy.bool` — more explicit, backward compatible with newer numpy.
- LU's `get_email_sendto_address()` (proper email quoting for names with special chars) is a genuine bug fix; apply it wherever email addresses are constructed.
- `fabfile.py` `loaddb`: improved pg_owner detection uses both `strings` and `pg_restore -l`; only drops `SCHEMA public` if the dump actually includes it (some `pg_dump` versions omit it for the default schema).

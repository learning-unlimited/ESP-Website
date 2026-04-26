#!/usr/bin/env python
"""Minimal Django environment bootstrap for ESP scripts.

This module sets up sys.path, activates the virtualenv if needed, configures
DJANGO_SETTINGS_MODULE, and calls django.setup(). It is intentionally *not*
setting DJANGO_IS_IN_SCRIPT so that the standard (non-script) logging handlers
and email-admins behaviour remain active for unattended scripts (e.g. cron
jobs and the mailgate) — see esp/esp/settings.py for details.

Usage (from any script living inside the ``esp/`` project directory or its
sub-directories)::

    import esp_setup  # noqa: F401 — imported for side-effects

After this import Django is fully configured and you can import any esp.* or
django.* symbol normally.
"""

import os
import sys
from io import open as io_open

# ---------------------------------------------------------------------------
# Locate the project root (the directory that contains manage.py).
# This file lives at <project>/esp_setup.py so its own directory *is* the
# project root, but we keep the calculation explicit so it stays correct if
# the file is ever moved one level deeper (e.g. into useful_scripts).
# ---------------------------------------------------------------------------
_this_file = os.path.realpath(__file__)
_project = os.path.dirname(_this_file)   # …/esp/

# Make sure the project root is on sys.path so that ``import esp.settings``
# and all other package imports work.
if _project not in sys.path:
    sys.path.insert(0, _project)

# ---------------------------------------------------------------------------
# Activate virtualenv only when one has *not* already been activated by the
# caller (the VIRTUAL_ENV env-var is set by virtualenv's activate script).
# ---------------------------------------------------------------------------
if os.environ.get('VIRTUAL_ENV') is None:
    _root = os.path.dirname(_project)
    _activate = os.path.join(_root, 'env', 'bin', 'activate_this.py')
    with io_open(_activate, 'rb') as _fh:
        exec(compile(_fh.read(), _activate, 'exec'), dict(__file__=_activate))

# ---------------------------------------------------------------------------
# Point Django at the right settings module, then bootstrap it.
# Use setdefault so that a caller can override the module before importing us.
# ---------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')

import django  # noqa: E402 — must follow sys.path / venv setup above
django.setup()

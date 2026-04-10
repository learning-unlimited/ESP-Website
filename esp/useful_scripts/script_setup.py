#!/usr/bin/env python
"""Bootstrap for interactive/useful scripts run from the useful_scripts dir.

Sets up the full shell-plus-style environment:
  * Django environment (via esp_setup)
  * All Django model classes injected into the caller's global namespace
  * Helper utilities from esp.utils.shell_utils (including DJANGO_IS_IN_SCRIPT)

Usage::

    from script_setup import *
"""

import os
import sys

# Ensure the project root (one level up from this file's directory) is on
# sys.path so that ``import esp_setup`` works regardless of the working
# directory from which the script is launched.
useful_scripts = os.path.dirname(os.path.realpath(__file__))
project = os.path.dirname(useful_scripts)
if project not in sys.path:
    sys.path.insert(0, project)

# Bootstrap the Django environment using the shared helper.
import esp_setup  # noqa: F401,E402 — imported for side-effects

# Inject all registered Django model classes into the calling script's
# namespace (replicates the shell_plus behaviour that scripts relied on).
from django.apps import apps  # noqa: E402
for _m in apps.get_models():
    globals()[_m.__name__] = _m

# Pull in shell utilities (also sets DJANGO_IS_IN_SCRIPT=True, which enables
# script-specific logging handlers and disables email-admins/sentry).
from esp.utils.shell_utils import *  # noqa: F401,F403,E402

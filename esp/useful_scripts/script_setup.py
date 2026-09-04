#!/usr/bin/env python
from pathlib import Path

import os, sys
from io import open

useful_scripts = Path(__file__).resolve().parent
project = useful_scripts.parent
sys.path.append(str(project))

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    envroot = project.parent
    activate_this = envroot / 'env' / 'bin' / 'activate_this.py'
    exec(compile(open(activate_this, "rb").read(), str(activate_this), 'exec'), dict(__file__=activate_this))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

from django.apps import apps
from django.conf import settings as S
import django

django.setup()

for m in apps.get_models():
    globals()[m.__name__] = m

from esp.utils.shell_utils import *

#!/usr/bin/env python

import os, sys

useful_scripts = os.path.dirname(os.path.realpath(__file__))
project = os.path.dirname(useful_scripts)
sys.path.append(project)

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    envroot = os.path.dirname(project)
    activate_this = os.path.join(envroot, 'env', 'bin', 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

from django.apps import apps
from django.conf import settings as S
import django

django.setup()

for m in apps.get_models():
    globals()[m.__name__] = m

from esp.utils.shell_utils import *

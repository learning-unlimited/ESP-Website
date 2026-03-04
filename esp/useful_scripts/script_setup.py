#!/usr/bin/env python

import os, sys
from io import open

useful_scripts = os.path.dirname(os.path.realpath(__file__))
project = os.path.dirname(useful_scripts)
sys.path.append(project)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

from django.apps import apps
from django.conf import settings as S
import django

django.setup()

for m in apps.get_models():
    globals()[m.__name__] = m

from esp.utils.shell_utils import *

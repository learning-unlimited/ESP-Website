#!/usr/bin/env python

import os, sys

useful_scripts = os.path.dirname(os.path.realpath(__file__))
project = os.path.dirname(useful_scripts)
sys.path.append(project)

# activate virtualenv
envroot = os.path.dirname(project)
activate_this = os.path.join(envroot, 'env', 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

from django.db.models.loading import get_models
from django.conf import settings as S

# http://sontek.net/blog/detail/tips-and-tricks-for-the-python-interpreter
for m in get_models():
    globals()[m.__name__] = m

from esp.utils.shell_utils import *

#!/usr/bin/python

import sys
sys.path += ['/esp/esp/']
sys.path += ['/esp/esp/esp/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp import cache_loader
import esp.manage
from esp.users.models import ESPUser

def check_password(environ, username, password):
    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)
    if user is not None:
	if user.is_active:
	    return True
    return False

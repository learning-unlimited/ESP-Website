#!/usr/bin/python

import sys
sys.path += ['/esp/web/mit/']
sys.path += ['/esp/web/mit/esp/']
sys.path += ['/esp/web/mit/django/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp import cache_loader
import esp.manage
from esp.users.models import ESPUser

def return_(val):
    """ Return the specified return value in the appropriate format """
    if val == True:
        sys.stdout.write("true")
        sys.exit(0)
    elif val == False:
        sys.stdout.write("false")
        sys.exit(1)
    else:
        sys.stdout.write(val)
        sys.exit(255)


args_raw = sys.stdin.read()
args = args_raw.split('\n')

assert len(args) >= 3, "Error: Must pass in action, username, and password"

action, username, password = args[:3]

if action == "USER_EXISTS":
    if len(ESPUser.objects.filter(username__iexact=username)[:1]) > 0:
        return_(True)
    else:
        return_(False)

elif action == "AUTHENTICATE":
    # aseering 7/11/2009 -- MediaWiki enforces that the first letter of usernames be capitalized and that lookups are
    # case-insensitive.  This isn't how Django works; so we can't use their "authenticate" builtin.
    #from django.contrib.auth import authenticate
    #user = authenticate(username=username, password=password)

    user = ESPUser.objects.get(username__iexact=username)
    if not user.check_password(password):
        return_(False)

    from esp.users.models import UserBit, GetNode
    if UserBit.UserHasPerms(user, GetNode("Q/Wiki"), GetNode("V/Administer"), recursive_required=True):
        return_(True)
    else:
        return_(False)

else:
    return_("ERROR_Unknown_Action")

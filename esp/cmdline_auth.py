#!/usr/bin/python

import sys
sys.path += ['/esp/web/mit/']
sys.path += ['/esp/web/mit/esp/']
sys.path += ['/esp/web/mit/django/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp import cache_loader
import esp.manage

def return_(val):
    """ Return the specified return value in the appropriate format """
    if val == True:
        print "true"
        sys.exit(0)
    elif val == False:
        print "false"
        sys.exit(1)
    else:
        print val
        sys.exit(255)


args = sys.stdin.read().split('\n')

assert len(args) >= 3, "Error: Must pass in action, username, and password"

action, username, password = args[:3]

if action == "USER_EXISTS":
    from esp.users.models import ESPUser
    if len(ESPUser.objects.filter(username=username)[:1]) > 0:
        return_(True)
    else:
        return_(False)

elif action == "AUTHENTICATE":
    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)
    if user is None:
        return_(False)

    from esp.users.models import UserBit, GetNode
    if UserBit.UserHasPerms(user, GetNode("Q/Wiki"), GetNode("V/Administer")):
        return_(True)
    else:
        return_(False)

else:
    return_("ERROR_Unknown_Action")

#!/usr/bin/python

####################
# Begin Configuration Variables
####################

path_to_esp = '/esp/esp/'
blanche_exec_template = "blanche -r -u -n %(email_name)s && blanche -r -k -n %(email_name)s 2>/dev/null"
blanche_nonrecursive_exec_template = "blanche -u -n %(email_name)s && blanche -k -n %(email_name)s 2>/dev/null"
admin_node = GetNode("V/Administer")
web_qsc_node = GetNode("Q/Web")
program_qsc_node = GetNode("Q/Programs")
custom_prog_email_mappings = { "Q/Programs": ("esp-officers", blanche_nonrecursive_exec_template),
                               "Q/Programs/SplashOnWheels": "splash-on-wheels",
                               "Q/Programs/ProveIt": "proveit" }

####################
# Begin Code
####################


# Generic setup code to be able to import esp stuff
import sys
sys.path += [path_to_esp]

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import esp.manage

from esp.users.models import ESPUser, UserBit
from esp.datatree.models import DataTree, GetNode
from datetime import datetime, timedelta

def clean(str):
    """ Return 'str', minus any characters not in the accept list """
    accepted_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
    lst = list(str)
    clean_list = []
    for ch in lst:
        if ch in accepted_chars:
            clean_list.append(ch)

    return ''.join(clean_list)

def dekrb(str):
    """ If we're given a "KERBEROS:username@ATHENA.MIT.EDU" string (which blanche returns if someone has added their Kerberos instance to a list but not themselves), strip the "KERBEROS:" and the "@ATHENA.MIT.EDU".  Then return the input string. """
    if str[:9] == "KERBEROS:" and st[-15:] == "@ATHENA.MIT.EDU":
        return str[9:-15]
    else:
        return str

# Iterate through all programs, to add bits
# Also scan through "esp-officers@".  Doing this within this loop has introduced several hacks, maybe more than it's worth...
for prog_node in list(program_qsc_node.children()) + [program_qsc_node]:

    # Most e-mail addresses are "$PROGRAM-admin@".  Some aren't.
    # Also, we want to grant bits on most to all people recursively on the list, but on some, we only want to grant bits to users directly on the list.
    # Handle the exceptions here:
    if prog_node.get_uri() in custom_prog_email_mappings:
        uri_mapping = custom_prog_email_mappings[ prog_node.get_uri() ]
        if type(uri_mapping) == str:
            email_name = uri_mapping
            blanche_exec = blanche_exec_template
        else:
            email_name = uri_mapping[0]
            blanche_exec = uri_mapping[1]
    # and the "Most" cases here
    else:
        email_name = clean( prog_node.name.lower() + "-admin" )
        blanche_exec = blanche_exec_template

    # Ask blanche who is on each list.  Note that we don't have Kerberos
    # tickets, so this only works for public lists
    # Do we want to include KERBEROS: users, users who only enter e-mails?
    users = os.popen(blanche_exec % { 'email_name': email_name })
    users_list = [dekrb(i.strip()) for i in users if i.strip() != '']
    users.close()

    for username in users_list:
        # This only works for people who add their @mit.edu address to the list,
        # _AND_ use their @mit.edu address for their esp.mit.edu account.
        # I don't know of a way that I trust that I'm unlazy enough 
        # to implement, that gets around this.
        user_email = username + "@mit.edu"
        
        user_set = ESPUser.objects.filter(username=username, email=user_email)

        # len(user_set) should always be either 0 or 1, by db constraint.
        # A "for" loop is the easiest way to handle this.
        for user in user_set:
            # Grant bits to the program, if needed
            if not UserBit.UserHasPerms(user, prog_node, admin_node):
                UserBit.objects.create(user=user, qsc=prog_node, verb=admin_node, startdate=datetime.now(), enddate = datetime.now() + timedelta(365), recursive=True)

            # Grant bits to the website, if needed
            if not UserBit.UserHasPerms(user, web_qsc_node, admin_node):
                UserBit.objects.create(user=user, qsc=web_qsc_node, verb=admin_node, startdate=datetime.now(), enddate = datetime.now() + timedelta(365), recursive=True)

#!/usr/bin/env python2
# Given a list of email addresses, disable the corresponding user accounts.

from script_setup import *

def yn(prompt):
    print prompt,
    r = raw_input()
    return r.strip().lower() == 'y'

def deactivate(email):
    users = ESPUser.objects.filter(email__iexact=email)
    if not users:
        print "No user found with email address <%s>" % users
        return
    if len(users) > 1:
        print "Multiple accounts found for email address <%s>:" % users
        for user in users:
            print "  %s (%s)" % (user.name(), user.email)
        if not yn("Deactivate *all* accounts? [y/N] "):
            print "Skipping."
            return

    for user in users:
        if not user.is_active:
            print "%s (%s) <%s> is already deactivated" % (user.name(), user.username, user.email)
            continue
        user.is_active = False
        user.save()
        print "%s (%s) <%s> deactivated!" % (user.name(), user.username, user.email)

def main():
    print "Enter a list of email addresses, one per line."
    print "End with a blank line."
    emails = []
    while True:
        e = raw_input().strip()
        if not e:
            break
        emails.append(e)
    for e in emails:
        deactivate(e)
    print "Done!"

if __name__=="__main__":
    main()

#!/usr/bin/env python2
"""Fix the subscription state of mailman.

This script attempts to fix the subscription set of mailman to somewhat better
reflect the active users on the website.  This is fairly defensive since we
don't know how things got the way they are.  It is intended to be run manually.

If an email address on the mailman announcements list has a corresponding
account, but all of its corresponding accounts are disabled, we remove it
from mailman.  If an email address not on the mailman announcements list
corresponds to an active user on the website, and all associated user accounts
are active, we add it to mailman.
"""

from script_setup import *
from esp import mailman
from esp.users.models import ESPUser

DRY_RUN = True


def update_membership(base_users, list_name, add=False, dry_run=DRY_RUN):
    current_members = set(mailman.list_contents(list_name))
    print """Updating list "%s", which currently has %s users.""" % (
        list_name, len(current_members))
    if dry_run:
        print "(This is a dry run.)"

    users_to_maybe_remove = ESPUser.objects.filter(is_active=False)
    users_not_to_remove = ESPUser.objects.filter(is_active=True)
    users_to_remove = users_to_maybe_remove.exclude(
        email__in=users_not_to_remove.values('email'))
    members_to_remove = current_members & set(
        users_to_remove.values_list('email', flat=True))
    print "Removing %s users..." % len(members_to_remove),
    if not dry_run:
        out, err = mailman.remove_list_member(list_name, members_to_remove)
        if out:
            print "stdout:"
            print out
        if err:
            print "sterr:"
            print err
    print "removed."

    if add:
        users_to_maybe_add = base_users.filter(is_active=True)
        users_not_to_add = ESPUser.objects.filter(is_active=False)
        users_to_add = users_to_maybe_add.exclude(
            email__in=users_not_to_add.values('email'))
        print "Adding %s users..." % len(users_to_add),
        if not dry_run:
            out, err = mailman.add_list_members(list_name, users_to_add)
            if out:
                print "stdout:"
                print out
            if err:
                print "sterr:"
                print err
        print "added."
    else:
        print "User adding disabled."

    new_members = mailman.list_contents(list_name)
    print """List "%s" now contains %s users.""" % (
        list_name, len(new_members))
    print


def update_lists(add=False, dry_run=DRY_RUN):
    students = ESPUser.objects.filter(
        groups=Group.objects.get(name='Student'),
        studentinfo__graduation_year__gte=2015,
        studentinfo__graduation_year__lte=2030,
        id__gte=50000)
    parents = ESPUser.objects.filter(
        groups=Group.objects.get(name='Guardian'),
        id__gte=50000)
    educators = ESPUser.objects.filter(
        groups=Group.objects.get(name='Educator'),
        id__gte=50000)
    update_membership(students | parents | educators, "announcements", add, dry_run)
    teachers = ESPUser.objects.filter(
        groups=Group.objects.get(name='Teacher'),
        id__gte=50000)
    update_membership(teachers, "teachers", add, dry_run)

if __name__ == '__main__':
    update_lists()

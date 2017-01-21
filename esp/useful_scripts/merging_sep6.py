#!/usr/bin/env python

"""
Identify groups of accounts to merge.

Feel free to change these important characteristics.
UNIQUENESS CRITERIA: (full name, date of birth)
FILTERING: Only student-only accounts with valid names and DOBs are considered for merging.
"""

from esp.users.models import *
from esp.users.models.forwarder import *
from esp.program.models import *

def get_dob(user):
    try:
        profile_current = user.registrationprofile_set.get(most_recent_profile=True)
    except:
        profile_current = user.getLastProfile()

    dob = None
    if profile_current.student_info and profile_current.student_info.dob:
        dob = profile_current.student_info.dob
    else:
        other_profiles = RegistrationProfile.objects.filter(user=user, student_info__isnull=False).order_by('-last_ts')
        for p in other_profiles:
            if p.student_info.dob:
                dob = p.student_info.dob
                break
    return dob

def get_duplicate_users():
    """ Find duplicate users based on their full name and birth date """

    user_groups = {}
    users = ESPUser.objects.all().order_by('id')
    non_dob_users = 0
    num_students = 0
    for user in users:
        #   Only consider users that are only students (hence skipping teachers and admins).
        ut = user.getUserTypes()
        if not (len(ut) == 1 and ut[0] == u'Student'):
            continue

        num_students += 1
        #   Try hard to find their DOB.
        name = user.name().lower()
        dob = get_dob(user)

        if dob is None:
            #   print 'Found user with no DOB: %s. Skipping.' % user.username
            continue
            """
            non_dob_users += 1
            pass
            """

        key = tuple([name, dob])
        if key not in user_groups:
            user_groups[key] = []
        user_groups[key].append(user)

    print 'Of %d users there were %d students, %d of which had no DOB marked.' % (users.count(), num_students, non_dob_users)
    return user_groups

def merge_group(group):
    #   Put highest numbered account at beginning of list
    group.sort(key=lambda x: -x.id)
    for acct in group[1:]:
        UserForwarder.forward(acct, group[0])
    print 'Merged accounts: %s <- [%s]' % (group[0].username, ', '.join(x.username for x in group[1:]))

ug = get_duplicate_users()
group_dict = {}
for u in ug.keys():
    x = len(ug[u])
    if x not in group_dict:
        group_dict[x] = []
    group_dict[x].append(u)

size_dict = {}
for key in group_dict:
    size_dict[key] = len(group_dict[key])

print 'Distribution of duplicate account numbers'
print size_dict

"""
Example usage
for key in ug:
    if len(ug[key]) > 1:
        merge_group(ug[key])
"""


from script_setup import *

import random
import datetime

def create_users_for_schools(program, groups, schools):
    """
    Create a sequentially numbered list of users for some schools, with a randomly generated
    password for each school.

    :param program:
       The program for which we should create these users.
    :param groups:
       The groups that all of these users should be added to.  IN ADDITION TO ANY OTHER DESIRED
       GROUPS, YOU MUST ADD EITHER THE "Student" or "Teacher" GROUP (probably the former in most
       use cases of this script); OTHERWISE, THE PROFILE VIEWER MAY FAIL.
    :param schools:
       A dictionary where the key is a string indicating the school and is the prefix
       for all the usernames; the value is the number of accounts desired for that school.  For
       example, if there is an item 'xyz' : 20, then the usernames will be xyz1, xyz2, ..., xyz20.
    :return:
       A dictionary where the key is a school prefix, and the value is the randomly generated
       password (which will start with the prefix).
    """
    ret = {}
    for school, number in schools.iteritems():
        pw = school + str(random.randrange(1000000))
        create_users_for_program(program, school + '{}', pw, groups, number)
        ret[school] = pw
    return ret


def create_users_for_program(program, username_format, password_format, groups, number=1):
    """Create a set of generic users for a program.

    Example use case: create one-time accounts for a HS's outreach students.

    :param program:
        Create a :class:`RegistrationProfile` for the user, with this as
        the value of the `program` field.
    :type program:
        :class:`Program` or None
    :param username_format:
        A format string for the usernames. Must contain exactly one '{}'
        substring. Generate usernames by formatting the string with the
        current index of iteration.
    :type username_format:
        `unicode`
    :param password_format:
        A format string for the password. Generate passwords by formatting
        the string with the current index of iteration. May contain no '{}'
        substrings, to reuse the same password for each user.
    :type password_format:
        `unicode`
    :param groups:
        A list of groups, specified by object or name, to add each new user
        to. Can also pass a single group or group name.
    :type groups:
        (`list` of (:class:`Group` or `unicode`)) or (:class:`Group` or `unicode`)
    :param number:
        A positive number of new users to create.
    :type number:
        `int`
    :return:
        A list of data dictionaries, one for each created user. Each
        dictionary contains 'username', 'password', 'user', and 'profile'
        keys.
    :rtype:
        `list` of `dict`
    """
    if not isinstance(groups, (list, tuple)):
        groups = [groups]
    groups = map(get_group, groups)
    ret = []
    for i in xrange(1, number + 1):
        username = username_format.format(i)
        password = password_format.format(i)
        ret.append(create_user_with_profile(username, password, program, groups))
    return ret


def get_group(group):
    if isinstance(group, Group):
        return group
    elif isinstance(group, basestring):
        return Group.objects.get(name=group)
    else:
        raise AssertionError('{} is not a Group or Group name'.format(unicode(group)))


def create_user_with_profile(username, password, program, groups):
    print "creating", username
    user = ESPUser.objects.create_user(username=username, password=password)
    user.groups.add(*groups)
    return {
        'username': username,
        'password': password,
        'user': user,
    }


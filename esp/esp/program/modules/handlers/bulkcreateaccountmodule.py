from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.utils.web import render_to_response
from esp.middleware import ESPError
from esp.users.models import ESPUser
from django.contrib.auth.models import Group
import random

class BulkCreateAccountModule(ProgramModuleObj):

    MAX_PREFIX_LENGTH = 30
    MAX_NUMBER_OF_ACCOUNTS = 1000  # backstop so that an errant request can't fill up the DB with accounts

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Bulk Create Accounts",
            "link_title": "Bulk Create Accounts",
            "module_type": "manage",
            "seq": 10,
            "choosable": 2,
        }

    @main_call
    @needs_admin
    def bulk_create_form(self, request, tl, one, two, module, extra, prog):
        context = {'groups': Group.objects.all().values_list('name', flat=True)}
        return render_to_response(self.baseDir() + 'bulk_create_form.html', request, context)

    @aux_call
    @needs_admin
    def bulk_account_create(self, request, tl, one, two, module, extra, prog):
        row_index = 0
        total_accounts = 0
        prefix_dict = {}
        while 'prefix' + str(1+row_index) in request.POST and 'count' + str(1+row_index) in request.POST:
            row_index += 1
            prefix = request.POST['prefix' + str(row_index)].strip()
            count = request.POST['count' + str(row_index)].strip()
            if prefix == '' and count == '': # skip blank row
                continue

            # validate data
            try:
                count = int(count)
            except ValueError:
                return self.bulk_account_error(request, 'Number of accounts must be a positive integer.')
            if count <= 0:
                return self.bulk_account_error(request, 'Number of accounts must be a positive integer.')
            if prefix == '':
                return self.bulk_account_error(request, 'Prefix cannot be empty.')
            if len(prefix) > self.MAX_PREFIX_LENGTH:
                return self.bulk_account_error(request, 'Prefix cannot be more than %d characters.'
                               % self.MAX_PREFIX_LENGTH)
            total_accounts += count
            if total_accounts > self.MAX_NUMBER_OF_ACCOUNTS:
                return self.bulk_account_error(request, 'Total number of accounts cannot be more than %d.'
                               % self.MAX_NUMBER_OF_ACCOUNTS)
            if prefix in prefix_dict:
                return self.bulk_account_error(request, 'Duplicate prefix: %s' % prefix)

            prefix_dict[prefix] = count

        if not prefix_dict:
            return self.bulk_account_error(request, 'You did not enter any accounts to create.')

        groups = []
        student_or_teacher = False
        for group_string in request.POST.getlist('groups'):
            if group_string in ('Student', 'Teacher'):
                student_or_teacher = True
            group = get_group(group_string)
            if group:
                groups.append(group)
            else:
                return self.bulk_account_error(request, 'There is no group named %s.' % group_string)
        if not student_or_teacher:
            return self.bulk_account_error(request, 'You must select either the Student or Teacher group, '
                            + 'in addition to any other groups you want.')

        result = create_users_for_schools(prog, groups, prefix_dict)
        context = {'passwords': result}

        return render_to_response(self.baseDir() + 'bulk_create_response.html', request, context)

    def bulk_account_error(self, request, message):
        context = {'bulk_account_error_message': message}
        return render_to_response(self.baseDir() + 'bulk_create_error.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'


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
        try:
            return Group.objects.get(name=group)
        except Group.DoesNotExist:
            return None
    else:
        raise ESPError('{} is not a Group or Group name'.format(unicode(group)))


def create_user_with_profile(username, password, program, groups):
    print "creating", username
    user = ESPUser.objects.create_user(username=username, password=password)
    user.groups.add(*groups)
    return {
        'username': username,
        'password': password,
        'user': user,
    }


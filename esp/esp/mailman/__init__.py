from __future__ import with_statement

from __future__ import absolute_import
import os
from subprocess import call, Popen, PIPE
from django.conf import settings
from esp.utils.decorators import enable_with_setting
from esp.users.models import ESPUser
from tempfile import NamedTemporaryFile
from django.contrib.auth.models import User
from django.db.models import Q
import six


if settings.USE_MAILMAN:
    MM_PATH = settings.MAILMAN_PATH
    MAILMAN_PASSWORD = settings.MAILMAN_PASSWORD
else:
    MAILMAN_PASSWORD = ''
    MM_PATH = "/usr/sbin/"

# Python 2 code for Mailman's config_list, which runs it with the list
# locked and saves the list (including approvals) afterwards. An exception
# here would stop config_list from saving the list's settings at all, so
# failures are caught and only reported.
RELEASE_NONMEMBER_HOLDS = """\
def _release_nonmember_holds(mlist):
    import sys
    from Mailman import mm_cfg
    from Mailman.Handlers.Hold import NonMemberPost
    for id in mlist.GetHeldMessageIds():
        try:
            if mlist.GetRecord(id)[3] == NonMemberPost.reason:
                mlist.HandleRequest(id, mm_cfg.APPROVE)
        except Exception, e:
            print >> sys.stderr, 'could not release held message %s: %s' % (id, e)
_release_nonmember_holds(mlist)
del _release_nonmember_holds
"""

## Functions for Mailman interop

@enable_with_setting(settings.USE_MAILMAN)
def create_list(list, owner, admin_password=MAILMAN_PASSWORD):
    """
    Create the specified mailing list in the local Mailman installation,
    with the address specified in 'owner' as the list's owners.

    If admin_password isn't specified, use the password from the local settings file.
    """
    if isinstance(owner, User):
        owner = owner.email

    return call([MM_PATH + "newlist", "-q", list, owner, admin_password])

@enable_with_setting(settings.USE_MAILMAN)
def load_list_settings(list, listfile):
    """
    Load a Mailman list-settings file and configure a list with the specified settings.

    If the path specified isn't an absolute path, it will be taken to be relative to the project root.
    """
    if listfile[0] == '/':
        listpath = listfile
    else:
        listpath = os.path.join(settings.PROJECT_ROOT, listfile)

    return call([MM_PATH + "config_list", "-i", listpath, list])


@enable_with_setting(settings.USE_MAILMAN)
def apply_raw_list_settings(list, data):
    """
    Apply the settings in 'data' to the specified list.
    This is functionally equivalent to writing 'data' to a file and calling "load_list_settings()" on that file.
    """
    with NamedTemporaryFile(mode="w") as f:
        f.write(data)
        f.file.flush()
        return call([MM_PATH + "config_list", "-i", f.name, list])


@enable_with_setting(settings.USE_MAILMAN)
def apply_list_settings(list, data, release_nonmember_holds=False):
    """
    Apply the settings in 'data' to the specified list.
    'data' is a key-value dictionary for Mailman variables to be set.
    Keys should be valid Python variable names expressed as strings.
    Values should be either strings, or objects that, when converted to a string via repr(), represent valid Python expressions in the configuration file.

    If 'release_nonmember_holds' is set, also approve every post the list is
    holding only because its sender isn't a member. Use it together with
    'generic_nonmember_action': 0 to make that setting cover posts that
    arrived before it was applied, e.g. while the list was being created.
    Both happen in one config_list run, which holds the list's lock, so no
    post can be held for that reason in between.
    """

    with NamedTemporaryFile(mode="w") as f:
        if release_nonmember_holds:
            f.write(RELEASE_NONMEMBER_HOLDS)
        f.writelines( ( "%s = %s\n" % (key, repr(value)) for key, value in six.iteritems(data) ) )
        f.file.flush()
        return call([MM_PATH + "config_list", "-i", f.name, list])


@enable_with_setting(settings.USE_MAILMAN)
def set_list_owner_password(list, password=None):
    """
    Set the list-owner password for the specified list.
    If 'password' isn't specified, a random password will be generated.
    Return the password that is ultimately used.
    """
    data_str_template = """import sha
mlist.password = sha.new('%s').hexdigest()
del sha
"""
    if not password:
        password = ESPUser.objects.make_random_password()

    data_str = data_str_template % (password)

    apply_raw_list_settings(list, data_str)
    return password


@enable_with_setting(settings.USE_MAILMAN)
def set_list_moderator_password(list, password=None):
    """
    Set the list-owner password for the specified list.
    If 'password' isn't specified, a random password will be generated.
    Return the password that is ultimately used.
    """
    data_str_template = """import sha
mlist.mod_password = sha.new('%s').hexdigest()
del sha
"""
    if not password:
        password = ESPUser.objects.make_random_password()

    data_str = data_str_template % (password)

    apply_raw_list_settings(list, data_str)
    return password


@enable_with_setting(settings.USE_MAILMAN)
def add_list_member(list_name, member):
    """Add the 'member' to the local Mailman mailing list 'list_name'.

    'member' may be a User object, or an email address.
    """
    return add_list_members(list_name, [member])


@enable_with_setting(settings.USE_MAILMAN)
def add_list_members(list_name, members):
    """Add email addresses to the local Mailman mailing list 'list_name'.

    'members' is an iterable of email address strings or ESPUser objects.
    """
    members = [x.get_email_sendto_address() if isinstance(x, User) else six.text_type(x) for x in members]

    members = six.u('\n').join(members)

    # encode as iso-8859-1 to match Mailman's daft Unicode handling, see:
    # http://bazaar.launchpad.net/~mailman-coders/mailman/2.1/view/head:/Mailman/Defaults.py.in#L1584
    # http://bazaar.launchpad.net/~mailman-coders/mailman/2.1/view/head:/Mailman/Utils.py#L822
    # this is probably fine since non-ASCII mostly happens in real names,
    # for which it doesn't matter much if we lose a few chars
    members = members.encode('iso-8859-1', 'replace')

    return Popen([MM_PATH + "add_members", "--regular-members-file=-", list_name], stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(members)

@enable_with_setting(settings.USE_MAILMAN)
def remove_list_member(list, member):
    """
    Remove the email address 'member' from the local Mailman mailing list 'list'

    "member" may be a list (or other iterable) of email address strings,
    in which case all addresses will be removed.
    """
    if isinstance(member, User):
        member = member.email

    if hasattr(member, "filter"):
        member = [x.email for x in member]

    if not isinstance(member, six.string_types):
        member = "\n".join(member)

    if isinstance(member, six.text_type):
        member = member.encode('iso-8859-1', 'replace')

    return Popen([MM_PATH + "remove_members", "--nouserack", "--noadminack", "--file=-", list], stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(member)

@enable_with_setting(settings.USE_MAILMAN)
def list_contents(lst):
    """ Return the list of email addresses on the specified mailing list """
    contents = Popen([MM_PATH + "list_members", lst], stdout=PIPE, stderr=PIPE).communicate()[0].decode('utf-8').split('\n')

    try:
        # It seems the empty string gets dragged into this list.
        contents.remove('')
    except:
        pass

    return contents

@enable_with_setting(settings.USE_MAILMAN)
def list_members(lst):
    """ Return the list (QuerySet) of ESPUsers who are on this mailing list """
    contents = list_contents(lst)
    usernames = [x[:-12] for x in contents if x[-12:] == "@esp.mit.edu"]
    return ESPUser.objects.filter(Q(email__in=contents) | Q(username__in=usernames))

@enable_with_setting(settings.USE_MAILMAN)
def all_lists(show_nonpublic=False):
    """
    Return the list of mailing lists served by this server.
    Mailing list names are returned as strings.
    Only lists flagged as 'advertised' in Mailman are returned unless show_nonpublic is True.
    """
    args = [MM_PATH + "list_lists", "-b"]
    if not show_nonpublic:
        args.append("-a")
    return Popen(args, stdout=PIPE, stderr=PIPE).communicate()[0].decode('utf-8').split('\n')

@enable_with_setting(settings.USE_MAILMAN)
def lists_containing(user):
    """ Return all lists that a user is a member of """
    if isinstance(user, six.string_types):
        search_regex="^%s$" % user
    else:
        search_regex = "^(%s|%s@%s)$" % (user.email, user.username, "esp.mit.edu")

    args = [MM_PATH + "find_member", search_regex]
    data = Popen(args, stdout=PIPE, stderr=PIPE).communicate()
    data = data[0].decode('utf-8').split('\n')

    # find_member's output is of the form
    #
    # [addr] found in:
    #     list1
    #     list2
    # [other_matching_addr] found in:
    #     list3
    #     list4
    #
    # We only want the lists; grab those:

    lists = [x.strip() for x in data]
    lists = [x for x in lists if x]
    return lists

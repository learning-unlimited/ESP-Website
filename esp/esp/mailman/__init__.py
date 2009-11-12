
from subprocess import call, Popen, PIPE
from esp.settings import USE_MAILMAN, PROJECT_ROOT
from esp.utils.decorators import enable_with_setting
from esp.database_settings import MAILMAN_PASSWORD
from esp.users.models import ESPUser, User

MM_PATH = "/usr/sbin/"

## Functions for Mailman interop

@enable_with_setting(USE_MAILMAN)
def create_list(list, owner, admin_password=MAILMAN_PASSWORD):
    """
    Create the specified mailing list in the local Mailman installation,
    with the address specified in 'owner' as the list's owners.

    If admin_password isn't specified, use the password from the local settings file.
    """
    if isinstance(owner, User):
        owner = owner.email

    return call([MM_PATH + "newlist", "-q", list, owner, admin_password])

@enable_with_setting(USE_MAILMAN)
def load_list_settings(list, listfile):
    """
    Load a Mailman list-settings file and configure a list with the specified settings.
   
    If the path specified isn't an absolute path, it will be taken to be relative to the project root.
    """
    if listfile[0] == '/':
        listpath = listfile
    else:
        listpath = PROJECT_ROOT + listfile

    return call([MM_PATH + "config_list", "-i", listpath, list])

@enable_with_setting(USE_MAILMAN)
def add_list_member(list, member):
    """
    Add the e-mail address 'member' to the local Mailman mailing list 'list'
    
    "member" may be a list (or other iterable) of e-mail address strings,
    in which case all addresses will be added.
    """
    if isinstance(member, User):
        member = member.email

    if hasattr(member, "filter"):
        member = [x.email for x in member]

    if not isinstance(member, basestring):       
        member = "\n".join(member)

    return Popen([MM_PATH + "add_members", "--regular-members-file=-", list], stdin=PIPE).communicate(member)

@enable_with_setting(USE_MAILMAN)
def remove_list_member(list, member):
    """
    Remove the e-mail address 'member' from the local Mailman mailing list 'list'
    
    "member" may be a list (or other iterable) of e-mail address strings,
    in which case all addresses will be removed.
    """
    if isinstance(member, User):
        member = member.email

    if hasattr(member, "filter"):
        member = [x.email for x in member]

    if not isinstance(member, basestring):       
        member = "\n".join(member)

    return Popen([MM_PATH + "remove_members", "--file=-", list], stdin=PIPE).communicate(member)

@enable_with_setting(USE_MAILMAN)
def list_contents(list):
    """ Return the list of e-mail addresses on the specified mailing list """
    return Popen([MM_PATH + "list_members", list]).communicate()[0].split('\n')

@enable_with_setting(USE_MAILMAN)
def list_members(list):
    """ Return the list (QuerySet) of ESPUsers who are on this mailing list """
    return ESPUser.objects.filter(email__in=list_contents(list))



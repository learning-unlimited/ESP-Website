from subprocess import call, Popen, PIPE
from esp.database_settings import MAILMAN_PASSWORD
from esp.users.models import ESPUser, User

## Functions for Mailman interop

def create_list(list, owner, admin_password=MAILMAN_PASSWORD):
    """
    Create the specified mailing list in the local Mailman installation,
    with the address specified in 'owner' as the list's owners.

    If admin_password isn't specified, use the password from the local settings file.
    """
    if isinstance(owner, User):
        owner = owner.email

    return call(["newlist", "-q", list, owner, admin_password])


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

    return Popen(["add_members", "--regular-members-file=-", list], stdin=PIPE).communicate(member)


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

    return Popen(["remove_members", "--file=-", list], stdin=PIPE).communicate(member)


def list_contents(list):
    """ Return the list of e-mail addresses on the specified mailing list """
    return Popen(["list_members", list]).communicate()[0].split('\n')


def list_members(list):
    """ Return the list (QuerySet) of ESPUsers who are on this mailing list """
    return ESPUser.objects.filter(email__in=list_contents(list))



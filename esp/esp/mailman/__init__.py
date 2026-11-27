from __future__ import with_statement

from __future__ import absolute_import
import functools
import logging
import os
import re
import shlex
import sys
import types
from subprocess import Popen, PIPE, TimeoutExpired
from django.conf import settings
from esp.utils.decorators import enable_with_setting
from esp.users.models import ESPUser
from tempfile import NamedTemporaryFile
from django.contrib.auth.models import User
from django.db.models import Q
import six

logger = logging.getLogger(__name__)


if settings.USE_MAILMAN:
    MM_PATH = settings.MAILMAN_PATH
    MAILMAN_PASSWORD = settings.MAILMAN_PASSWORD
else:
    MAILMAN_PASSWORD = ''
    MM_PATH = "/usr/sbin/"

# Python 2 code for Mailman's config_list, which runs it with the list
# locked and saves the list (including approvals) afterwards. An exception
# here would stop config_list from saving the list's settings at all, so
# failures are caught and only reported, on stdout (the old esp-web SSH
# wrapper, MAILMAN_PATH=/esp/fake_mailman_bin/, drops a successful command's
# stderr).
RELEASE_NONMEMBER_HOLDS = """\
def _release_nonmember_holds(mlist):
    from Mailman import mm_cfg
    from Mailman.Handlers.Hold import NonMemberPost
    for id in mlist.GetHeldMessageIds():
        try:
            if mlist.GetRecord(id)[3] == NonMemberPost.reason:
                mlist.HandleRequest(id, mm_cfg.APPROVE)
        except Exception, e:
            print 'could not release held message %s: %s' % (id, e)
_release_nonmember_holds(mlist)
del _release_nonmember_holds
"""

class MailmanError(Exception):
    """ A Mailman command failed. The functions below raise it by default; see
    errors= below. """


def _mailman_argv(command, args):
    """ The argv that runs Mailman's 'command' (e.g. "list_members") with
    'args'.

    With settings.MAILMAN_SSH, a dict like

        {'host': 'esp-mail', 'user': 'espweb', 'key': '/path/to/id_rsa',
         'known_hosts': '/path/to/known_hosts', 'control_dir': '/run/esp-mailman',
         'persist': 30, 'options': ['PubkeyAcceptedAlgorithms=+ssh-rsa']}

    it runs "sudo <command> <args>" on that host with OpenSSH. Every argument
    is shell-quoted: the remote shell parses the command line, so an
    unquoted argument (e.g. a user's email in find_member's regex) could run
    commands there. Calls share one SSH connection (ControlMaster), kept open
    'persist' seconds (default 30) after the last use, so a burst of calls
    costs one handshake; 'control_dir' (created if missing, mode 700) holds
    its socket. ServerAlive gives up on a connection that stops answering in
    about 10 s. 'key' must be readable by its owner only, or OpenSSH ignores
    it. 'options' are extra ssh -o options.

    Without it, it runs MAILMAN_PATH + command locally (Mailman's bin
    directory, or a wrapper with the same command names). """
    ssh = getattr(settings, 'MAILMAN_SSH', None)
    if not ssh:
        return [MM_PATH + command] + list(args)
    control_dir = ssh['control_dir']
    if not os.path.isdir(control_dir):
        os.makedirs(control_dir, mode=0o700, exist_ok=True)
    options = [
        'IdentitiesOnly=yes',
        'BatchMode=yes',
        'StrictHostKeyChecking=yes',
        'UserKnownHostsFile=%s' % ssh['known_hosts'],
        'ControlMaster=auto',
        'ControlPath=%s' % os.path.join(control_dir, '%C'),
        'ControlPersist=%d' % ssh.get('persist', 30),
        'ServerAliveInterval=5',
        'ServerAliveCountMax=2',
        'LogLevel=ERROR',
    ] + list(ssh.get('options', ()))
    argv = ['ssh', '-i', ssh['key']]
    for option in options:
        argv += ['-o', option]
    remote = ' '.join(shlex.quote(a) for a in ['sudo', command] + list(args))
    return argv + ['%s@%s' % (ssh['user'], ssh['host']), remote]


def _run_checked(command, args, list_name, input=b'', ok_output=None):
    """ Run Mailman's 'command' with 'args' (see _mailman_argv) and raise
    MailmanError if it fails.

    Mailman's commands exit non-zero for errors that stop them, e.g. "No such
    list", and SSH (or the old wrapper) passes that status on.
    Some errors only show in the output (it can be on stdout or stderr), so
    'ok_output', if given, is called with the output and returns an error
    message, or None if all is well. Returns the command's stdout: stderr
    is only checked, never parsed (on a host where it isn't dropped, a
    warning there would otherwise read as a list member or name).

    The message names the command and list but never the arguments: newlist's
    include the list admin password.

    A command still running after MAILMAN_TIMEOUT seconds (default 30; the
    slowest normal one, list_lists, takes about 6) is a failure, so a hung
    esp-mail or SSH connection can't hold a web request indefinitely. """
    try:
        proc = Popen(_mailman_argv(command, args), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except OSError as e:
        # e.g. no such command (a local Mailman has no 'ls'), or no ssh. Not
        # str(e): it can name the arguments.
        raise MailmanError('%s %s: could not run: %s' % (command, list_name, e.strerror))
    timeout = getattr(settings, 'MAILMAN_TIMEOUT', 30)
    try:
        out, err = proc.communicate(input, timeout=timeout)
    except TimeoutExpired:
        # Stops this end only: Mailman may still finish the command.
        proc.kill()
        proc.communicate()
        raise MailmanError('%s %s: no answer after %s s' % (command, list_name, timeout))
    output = (out + err).decode('utf-8', 'replace').strip()
    problem = None
    if proc.returncode != 0:
        problem = 'exit status %s' % proc.returncode
    elif ok_output:
        problem = ok_output(output)
    if problem:
        # Mailman's commands print their usage text before the error itself,
        # so keep only the last few lines.
        tail = ' / '.join([l.strip() for l in output.splitlines() if l.strip()][-3:])
        raise MailmanError('%s %s: %s: %s' % (command, list_name, problem, tail[-500:]))
    return out.decode('utf-8', 'replace')


def _loggable(exc, frame):
    """ exc_info for logging exc: a copy of it whose traceback runs from where
    exc was caught outward through 'frame' and its callers. A caught
    exception's traceback only runs from the try to the raise, so without
    this a logged failure (and its Bugsink issue) wouldn't show which code ran
    the Mailman command.

    Nothing from inside the Mailman function is kept: Bugsink gets each
    frame's local variables, and those frames hold the list admin password
    (create_list, newlist's arguments) or a new moderator password. So the
    copy drops the frames below the catch and any chained exception (e.g.
    create_list's failed "does the list exist?" check), which carry their own
    frames. The message already says which command failed. """
    copy = MailmanError(str(exc))
    caught = exc.__traceback__
    tb = types.TracebackType(None, caught.tb_frame, caught.tb_lasti, caught.tb_lineno)
    while frame is not None:
        tb = types.TracebackType(tb, frame, frame.f_lasti, frame.f_lineno)
        frame = frame.f_back
    return (MailmanError, copy.with_traceback(tb), tb)


def _mailman_command(empty=None):
    """ Give a Mailman function an 'errors' keyword argument saying what to do
    when its command fails, like bytes.decode(errors=...):

        'raise' (default)  raise MailmanError
        'log'              log the failure, with the traceback of the code
                           that called the function (it reaches Bugsink),
                           and carry on
        'ignore'           carry on silently, e.g. for a class list that
                           usually doesn't exist yet

    After a failure under 'log' or 'ignore' the function returns 'empty()'
    (None for commands that change something, [] for ones that read), so only
    'raise' tells "failed" apart from "nothing there". """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, errors='raise', **kwargs):
            if errors not in ('raise', 'log', 'ignore'):
                raise ValueError("errors must be 'raise', 'log' or 'ignore', not %r" % (errors,))
            try:
                return func(*args, **kwargs)
            except MailmanError as e:
                if errors == 'raise':
                    raise
                if errors == 'log':
                    logger.error('Mailman command failed: %s', e,
                                 exc_info=_loggable(e, sys._getframe(1)))
                return empty() if empty else None
        return wrapper
    return decorate


## Functions for Mailman interop
#
# Each takes errors='raise' | 'log' | 'ignore' (see _mailman_command). Those
# that change something return None; on failure they raise, or with 'log' or
# 'ignore' return None.

@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def create_list(list, owner, admin_password=MAILMAN_PASSWORD):
    """
    Create the specified mailing list in the local Mailman installation,
    with the address specified in 'owner' as the list's owners.

    If admin_password isn't specified, use the password from the local settings file.

    A list that already exists (e.g. two first emails to it arrived at once)
    is not a failure. Returns True if the list was created, False if it
    already existed (None under errors='log' or 'ignore' after a failure).
    """
    if isinstance(owner, User):
        owner = owner.email

    try:
        _run_checked("newlist", ["-q", list, owner, admin_password], list)
        return True
    except MailmanError as e:
        # The old esp-web SSH wrapper replaces a failed command's output with
        # its own message, so "List already exists" can't be read from it.
        # Ask whether the list is there instead.
        try:
            _run_checked("list_members", [list], list)
        except MailmanError:
            raise e
        return False


def _config_list_problems(output):
    """ Our own code run inside config_list (RELEASE_NONMEMBER_HOLDS) only
    prints its failures. (config_list also exits 0 when it rejects a
    setting's value, but says so on stderr, which the old esp-web SSH wrapper
    drops, so that isn't checked here.) """
    bad = [line for line in output.splitlines()
           if 'could not release held message' in line]
    return '; '.join(bad) or None


def _config_list(data, list):
    """ Run config_list -i on 'list' with 'data', Python 2 source (a str):
    over SSH it goes on stdin, else in a temporary file. """
    if getattr(settings, 'MAILMAN_SSH', None):
        _run_checked("config_list", ["-i", "/dev/stdin", list], list,
                     input=data.encode('utf-8'), ok_output=_config_list_problems)
        return
    with NamedTemporaryFile(mode="w") as f:
        f.write(data)
        f.file.flush()
        _run_checked("config_list", ["-i", f.name, list], list,
                     ok_output=_config_list_problems)


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def load_list_settings(list, listfile):
    """
    Load a Mailman list-settings file and configure a list with the specified settings.

    If the path specified isn't an absolute path, it will be taken to be relative to the project root.
    """
    _config_list(_read_list_settings(listfile), list)


def _read_list_settings(listfile):
    if listfile[0] == '/':
        listpath = listfile
    else:
        listpath = os.path.join(settings.PROJECT_ROOT, listfile)
    with open(listpath) as f:
        text = f.read()
    return text if text.endswith('\n') else text + '\n'


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def apply_raw_list_settings(list, data):
    """
    Apply the settings in 'data' to the specified list.
    This is functionally equivalent to writing 'data' to a file and calling "load_list_settings()" on that file.
    """
    _config_list(data, list)


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def apply_list_settings(list, data, release_nonmember_holds=False, listfile=None):
    """
    Apply the settings in 'data' to the specified list, after those of the
    list-settings file 'listfile' if given (as for load_list_settings; one
    config_list run instead of two).
    'data' is a key-value dictionary for Mailman variables to be set.
    Keys should be valid Python variable names expressed as strings.
    Values should be either strings, or objects that, when converted to a string via repr(), represent valid Python expressions in the configuration file.

    If 'release_nonmember_holds' is set, also approve every post the list is
    holding only because its sender isn't a member, e.g. posts that arrived
    while a new list was being created, before 'generic_nonmember_action': 0
    was applied. This runs in one config_list run, which holds the list's
    lock, so no post can be held for that reason in between. An approved
    post goes out at once to the list's members as they are then, so add
    the members first. A held post that can't be released is a failure.
    """

    text = _read_list_settings(listfile) if listfile else ''
    text += RELEASE_NONMEMBER_HOLDS if release_nonmember_holds else ''
    text += ''.join("%s = %s\n" % (key, repr(value)) for key, value in six.iteritems(data))
    _config_list(text, list)


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def set_list_owner_password(list, password=None):
    """
    Set the list-owner password for the specified list.
    If 'password' isn't specified, a random password will be generated.
    Return the password that is ultimately used (None if it couldn't be set).
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
@_mailman_command()
def set_list_moderator_password(list, password=None):
    """
    Set the list-moderator password for the specified list.
    If 'password' isn't specified, a random password will be generated.
    Return the password that is ultimately used (None if it couldn't be set).
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


def _addresses(members, formatted):
    """ The addresses in 'members' (one member, or an iterable or QuerySet of
    them; each a User or an email address string), leaving out blank ones: a
    User with no email, None, or an empty or whitespace string. Mailman would
    refuse those, and a blank address isn't a failure worth reporting. Users
    become their "Name" <email> address if 'formatted', else their email. """
    if isinstance(members, (User, six.string_types)):
        members = [members]
    addresses = []
    for x in members:
        if isinstance(x, User):
            if (x.email or '').strip():
                addresses.append(x.get_email_sendto_address() if formatted else x.email.strip())
        elif x is not None and six.text_type(x).strip():
            addresses.append(six.text_type(x).strip())
    return addresses


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def add_list_member(list_name, member):
    """Add the 'member' to the local Mailman mailing list 'list_name'.

    'member' may be a User object, or an email address.
    """
    add_list_members(list_name, [member])


def _add_members_problems(output):
    """ add_members exits 0 when it skips an address it won't accept. """
    bad = [line for line in output.splitlines()
           if line.startswith(('Bad/Invalid email address', 'Hostile address'))]
    return '; '.join(bad) or None


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def add_list_members(list_name, members):
    """Add email addresses to the local Mailman mailing list 'list_name'.

    'members' is an iterable of email address strings or ESPUser objects.
    Blank addresses are skipped (see _addresses); with none left, Mailman
    isn't called.

    A refused address is a failure (the others are still added); one that is
    already a member is not.
    """
    members = _addresses(members, formatted=True)
    if not members:
        return

    members = six.u('\n').join(members)

    # encode as iso-8859-1 to match Mailman's daft Unicode handling, see:
    # http://bazaar.launchpad.net/~mailman-coders/mailman/2.1/view/head:/Mailman/Defaults.py.in#L1584
    # http://bazaar.launchpad.net/~mailman-coders/mailman/2.1/view/head:/Mailman/Utils.py#L822
    # this is probably fine since non-ASCII mostly happens in real names,
    # for which it doesn't matter much if we lose a few chars
    members = members.encode('iso-8859-1', 'replace')

    _run_checked("add_members", ["--regular-members-file=-", list_name],
                 list_name, input=members, ok_output=_add_members_problems)


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def remove_list_member(list, member):
    """
    Remove the email address 'member' from the local Mailman mailing list 'list'

    "member" may be a User, or a list (or other iterable, or QuerySet) of
    email address strings or Users, in which case all addresses will be
    removed. Blank addresses are skipped (see _addresses); with none left,
    Mailman isn't called.

    An address that isn't on the list is not a failure.
    """
    member = _addresses(member, formatted=False)
    if not member:
        return
    member = "\n".join(member).encode('iso-8859-1', 'replace')

    # remove_members exits 0 even when it can't open the list. (It says so on
    # stderr, which the old esp-web SSH wrapper drops on success: there, a
    # missing list goes unreported. MAILMAN_SSH keeps stderr.)
    _run_checked("remove_members", ["--nouserack", "--noadminack", "--file=-", list],
                 list, input=member,
                 ok_output=lambda out: out if 'Error opening list' in out else None)


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command(empty=list)
def list_contents(lst):
    """ Return the list of email addresses on the specified mailing list.
    No such list is a failure, not an empty list. """
    output = _run_checked("list_members", [lst], lst)
    return [line.strip() for line in output.split("\n") if line.strip()]


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command(empty=list)
def list_members(lst):
    """ Return the list (QuerySet) of ESPUsers who are on this mailing list """
    contents = list_contents(lst)
    usernames = [x[:-12] for x in contents if x[-12:] == "@esp.mit.edu"]
    return ESPUser.objects.filter(Q(email__in=contents) | Q(username__in=usernames))


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command(empty=list)
def all_lists(show_nonpublic=False):
    """
    Return the list of mailing lists served by this server.
    Mailing list names are returned as strings.
    Only lists flagged as 'advertised' in Mailman are returned unless show_nonpublic is True.
    """
    args = ["-b"]
    if not show_nonpublic:
        args.append("-a")
    return [line.strip() for line in _run_checked("list_lists", args, '(all lists)').split('\n') if line.strip()]


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command(empty=set)
def existing_lists():
    """ The names (lower case) of all Mailman lists, public or not: the same
    lists as all_lists(show_nonpublic=True), in about 0.1 s instead of 6.
    Mailman keeps each list in a directory of MAILMAN_LISTS_DIR, named after
    the list, which newlist creates and rmlist deletes, and list_lists is
    slow only because it then loads every list. (A directory left without
    its config.pck, a broken list, counts too; commands on it fail and are
    reported as usual.) Needs an 'ls' next to the Mailman commands (the
    esp-web SSH wrapper has one) or MAILMAN_SSH. """
    lists_dir = getattr(settings, 'MAILMAN_LISTS_DIR', '/var/lib/mailman/lists')
    output = _run_checked("ls", ["-1", lists_dir], '(all lists)')
    return set(line.strip().lower() for line in output.split('\n') if line.strip())


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command()
def sync_list_members(list_name, members, keep=()):
    """ Make the members of the Mailman list 'list_name' exactly 'members'
    (Users or email address strings, as for add_list_members), leaving any
    member whose address is in 'keep' alone. Three Mailman calls at most:
    one to read the list, one to remove, one to add, however many members
    change. Addresses compare case-insensitively, as in Mailman. """
    current = list_contents(list_name)
    current_lower = set(address.lower() for address in current)
    wanted = {}
    for member in members:
        address = _addresses(member, formatted=False)
        if address:
            wanted.setdefault(address[0].lower(), member)
    keep = set(address.lower() for address in _addresses(list(keep), formatted=False))
    remove_list_member(list_name, [address for address in current
                                   if address.lower() not in wanted and address.lower() not in keep])
    add_list_members(list_name, [member for address, member in wanted.items()
                                 if address not in current_lower])


@enable_with_setting(settings.USE_MAILMAN)
@_mailman_command(empty=list)
def lists_containing(user):
    """ Return all lists that a user is a member of. 'user' is a User (found
    by email or username@esp.mit.edu) or an email address. A blank address
    matches nothing. """
    if isinstance(user, six.string_types):
        addresses = [user.strip()]
    else:
        addresses = [(user.email or '').strip(), user.username + "@esp.mit.edu"]
    addresses = [a for a in addresses if a]
    if not addresses:
        return []
    # find_member takes a regex; an address like a+b@x.com must match itself.
    search_regex = "^(%s)$" % "|".join(re.escape(a) for a in addresses)

    output = _run_checked("find_member", [search_regex], '(all lists)')

    # find_member's output is of the form
    #
    # [addr] found in:
    #     list1
    #     list2
    # [other_matching_addr] found in:
    #     list3
    #
    # We only want the list names: the indented lines. (With -w, which we
    # don't pass, it also prints "list4 (as owner)" lines; those are lists the
    # address owns, not ones it's a member of, so skip them in case.)
    return sorted(set(line.split()[0] for line in output.split('\n')
                      if line[:1].isspace() and line.strip() and '(as ' not in line))



class BaseHandler(object):

    send = False
    preserve_headers = False

    def __init__(self, handler, message):
        self.handler = handler
        self.message = message

    def process(self, *args, **kwargs):
        raise NotImplementedError


import email.utils


def sender_account(message):
    """Return the ESPUser who sent `message`, or None if its From address does
    not belong to an account on this site.

    Where several accounts share a From address the most privileged one wins
    (administrator, then teacher), falling back to the earliest account created.
    """
    from esp.users.models import ESPUser  # imported late to avoid a circular import

    _name, address = email.utils.parseaddr(message.get('From', ''))
    if not address:
        return None

    users = list(ESPUser.objects.filter(email__iexact=address))
    if not users:
        return None
    if len(users) == 1:
        return users[0]

    def rank(user):
        if user.isAdministrator():
            return 0
        if user.isTeacher():
            return 1
        return 2

    return sorted(users, key=lambda user: (rank(user), user.id))[0]

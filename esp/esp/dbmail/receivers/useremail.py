

from django.conf import settings

from esp.dbmail.base import BaseHandler, sender_account
from esp.users.models import ESPUser


class UserEmail(BaseHandler):

    def process(self, user, user_match):
        try:
            recipient = ESPUser.objects.get(username__iexact = user)
        except ESPUser.DoesNotExist:
            return

        # A staff alias accepts mail from any registered sender.
        # Everyone else's alias only accepts mail from staff.
        recipient_is_staff = recipient.isTeacher() or recipient.isAdministrator()
        sender = sender_account(self.message)
        sender_is_staff = (sender is not None
                           and (sender.isTeacher() or sender.isAdministrator()))

        # Allow mailing aliases to still work for local Mailman messages, but only
        # where Mailman is actually in use: otherwise any sender could add a
        # List-Id header of their own to bypass the rule above.
        from_mailman = (bool(self.message['List-Id'])
                        and getattr(settings, 'USE_MAILMAN', False))

        if recipient_is_staff or sender_is_staff or from_mailman:
            self.recipients = [recipient.email]
            self.preserve_headers = True
            self.send = True

        return

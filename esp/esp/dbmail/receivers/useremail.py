

from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser


class UserEmail(BaseHandler):

    def process(self, user, user_match):
        try:
            user = ESPUser.objects.get(username__iexact = user)
        except ESPUser.DoesNotExist:
            return

        # Allow mailing aliases to still work for local Mailman messages
        if user.isTeacher() or self.message['List-Id']:
            self.recipients = [user.email]
            self.preserve_headers = True
            self.send = True

        return

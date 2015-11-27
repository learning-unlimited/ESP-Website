

from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser


class UserEmail(BaseHandler):

    def process(self, user, user_match):
        try:
            user = ESPUser.objects.get(username__iexact = user)
        except ESPUser.DoesNotExist:
            return

        # DIRTY HACK to allow mailing aliases to still work for local Mailman messages
        if user.isTeacher() or self.message['List-Id']:
            del(self.message['to'])
            self.message['to'] = user.email
            self.direct_send = True
            self.send = True

        return

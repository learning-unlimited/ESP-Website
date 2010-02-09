

from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser


class UserEmail(BaseHandler):

    def process(self, user, user_match):
        try:
            user = ESPUser.objects.get(username__iexact = user)
        except ESPUser.DoesNotExist:
            return

        user = ESPUser(user)

        if user.isTeacher() or (self.message['List-Id'] and (".esp.mit.edu" in self.message['List-Id'])):
            #self.recipients = ['%s <%s>' % (user.name(),
            #                                user.email)]

            del(self.message['to'])
            self.message['to'] = user.email
            self.direct_send = True
            self.send = True

        return

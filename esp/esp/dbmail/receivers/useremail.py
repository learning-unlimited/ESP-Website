

from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser


class UserEmail(BaseHandler):

    def process(self, user, user_match):
        try:
            user = ESPUser.objects.get(username__iexact = user)
        except ESPUser.DoesNotExist:
            return

        user = ESPUser(user)

        if user.isTeacher():
            self.recipients = ['%s <%s>' % (user.name(),
                                            user.email)]
            self.send = True

        return

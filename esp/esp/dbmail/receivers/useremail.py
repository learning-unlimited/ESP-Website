

from esp.dbmail.models.base import BaseHandler
from esp.users.models import ESPUser


class UserEmail(BaseHandler):

    def process(self, user):
        try:
            user = ESPUser.object.get(username = user)
        except ESPUser.DoesNotExist:
            return

        user = ESPUser(user)

        if user.isTeacher():
            self.recipients = ['%s <%s>' % (user.name(),
                                            user.email)]
            self.send = True

        return

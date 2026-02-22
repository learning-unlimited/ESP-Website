

from esp.dbmail.base import BaseHandler
from esp.dbmail.models import PlainRedirect

class PlainList(BaseHandler):

    def process(self, user, user_match):

        redirects = PlainRedirect.objects.filter(original__iexact = user)

        if len(redirects.values('id')[:1]) == 0:
            return

        self.recipients = [redirect.destination for redirect in redirects]

        self.send = True

        return

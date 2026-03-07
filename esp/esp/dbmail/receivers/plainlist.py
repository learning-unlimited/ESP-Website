

from esp.dbmail.base import BaseHandler
from esp.dbmail.models import PlainRedirect

class PlainList(BaseHandler):

    def process(self, user, user_match):

        redirects = PlainRedirect.objects.filter(original__iexact = user)

        if len(redirects.values('id')[:1]) == 0:
            return

        self.recipients = []
        for redirect in redirects:
            for addr in redirect.destination.split(','):
                addr = addr.strip()
                if addr:
                    self.recipients.append(addr)

        self.send = True

        return

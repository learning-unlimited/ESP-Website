""" Models for the Queue. """
from django.conf import settings
from django.db import models

QUEUE_FILE = settings.TEMPLATE_DIRS[0] + '/errors/queue.html'
WELCOME_SCREEN = settings.TEMPLATE_DIRS[0] + '/queue_welcome.html'

class UserQueue(models.Model):
    browser = models.CharField(max_length=64)
    time_in_queue = models.DateTimeField(auto_now_add=True)
    time_since_last_refresh = models.DateTimeField(auto_now=True)
    in_site = models.BooleanField(default=False)

    def __unicode__(self):
        if self.in_site:
            return "In:     (%s) (%s) %s" % (self.time_since_last_refresh, self.time_in_queue, self.browser)
        else:
            return "Not In: (%s) (%s) %s" % (self.time_since_last_refresh, self.time_in_queue, self.browser)

    class Admin:
        pass

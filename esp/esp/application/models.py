from django.db import models
from esp.users.models import ESPUser
from esp.program.models import Program

class FsStudentApp(models.Model):
    """ A student's application. """

    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(ESPUser)
    program = models.ForeignKey(Program)
    coreclass1 = models.CharField(max_length=80)
    coreclass2 = models.CharField(max_length=80)
    coreclass3 = models.CharField(max_length=80)
    # to add: admin status, admin comment, teacher rating?, etc.

    def __unicode__(self):
        return "{}'s app for {}".format(self.user, self.program)

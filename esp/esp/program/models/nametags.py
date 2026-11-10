from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from reversion import revisions as reversion

__all__ = ['NametagBack']


@python_2_unicode_compatible
class NametagBack(models.Model):
    """A program's saved design for the back of a nametag, written in LaTeX.

    Used by the nametag module.  Any back can be printed with any category of
    nametag; the name is only a label for admins.  History is kept by
    django-reversion: save inside reversion.create_revision() so that a version
    is recorded.
    """
    name = models.CharField(max_length=100)
    program = models.ForeignKey('program.Program', models.CASCADE, related_name='nametag_backs')
    source = models.TextField()

    class Meta:
        app_label = 'program'
        unique_together = (('program', 'name'),)

    def __str__(self):
        return '%s: %s' % (self.program.niceName(), self.name)

reversion.register(NametagBack)

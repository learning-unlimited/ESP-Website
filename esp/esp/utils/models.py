__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from django.db import models
from reversion import revisions as reversion

from esp.users.models import ESPUser
from esp.db.fields import AjaxForeignKey

""" A template override model that stores the contents of a template in the database. """
class TemplateOverride(models.Model):

    name = models.CharField(max_length=255, help_text='The filename (relative path) of the template to override.')
    content = models.TextField()
    version = models.IntegerField()

    class Meta:
        unique_together = (('name', 'version'), )

    def __unicode__(self):
        return 'Ver. %d of %s' % (self.version, self.name)

    def next_version(self):
        qs = TemplateOverride.objects.filter(name=self.name)
        if qs.exists():
            return qs.order_by('-version').values_list('version', flat=True)[0] + 1
        else:
            return 1

    def save(self, *args, **kwargs):
        #   Never overwrite; save a new copy with the version incremented.
        self.version = self.next_version()
        super(TemplateOverride, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return "/manage/templateoverride/" + str(self.id)


class Printer(models.Model):
    name = models.CharField(max_length=255, help_text='Name to display in onsite interface')
    printer_type = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __unicode__(self):
        return self.name

class PrintRequest(models.Model):
    printer = models.ForeignKey(Printer, blank=True, null=True)     #   Leave blank to allow any printer to be used.
    user = AjaxForeignKey(ESPUser)
    time_requested = models.DateTimeField(auto_now_add=True)
    time_executed = models.DateTimeField(blank=True, null=True)

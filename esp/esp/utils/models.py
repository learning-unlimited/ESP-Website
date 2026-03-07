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
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
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

    def __str__(self):
        return f'Ver. {self.version} of {self.name}'

    def next_version(self):
        qs = TemplateOverride.objects.filter(name=self.name)
        if qs.exists():
            return qs.order_by('-version').values_list('version', flat=True)[0] + 1
        else:
            return 1

    def save(self, *args, **kwargs):
        #   Never overwrite; save a new copy with the version incremented.
        self.version = self.next_version()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return "/manage/templateoverride/" + str(self.id)

class Printer(models.Model):
    name = models.CharField(max_length=255, help_text='Name to display in onsite interface')
    printer_type = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name

class PrintRequest(models.Model):
    printer = models.ForeignKey(Printer, blank=True, null=True, on_delete=models.CASCADE)     #   Leave blank to allow any printer to be used.
    user = AjaxForeignKey(ESPUser, on_delete=models.CASCADE)
    time_requested = models.DateTimeField(auto_now_add=True)
    time_executed = models.DateTimeField(blank=True, null=True)


class AuditLogEntry(models.Model):
    """
    Immutable record of a sensitive admin action.
    Written by AuditedModelAdmin whenever an object is saved or deleted
    through the Django admin interface.

    Cross-app infrastructure — lives in esp.utils, not in any single app.
    """

    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_BULK   = 'bulk_action'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_BULK,   'Bulk action'),
    ]

    actor        = models.ForeignKey(
        ESPUser, null=True, on_delete=models.SET_NULL,
        related_name='audit_log_entries',
        help_text='Admin user who performed the action.',
    )
    action       = models.CharField(max_length=16, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL,
        help_text='Django ContentType of the affected model.',
    )
    object_id    = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Primary key of the affected object.',
    )
    object_repr  = models.TextField(blank=True, help_text='str() of the object at action time.')
    changes      = JSONField(
        null=True, blank=True,
        help_text='JSON dict of {field: [old_value, new_value]} for updates.',
    )
    actor_ip     = models.GenericIPAddressField(
        null=True, blank=True,
        help_text='IP address of the admin user at action time.',
    )
    extra        = models.TextField(
        blank=True,
        help_text='Free-text note, e.g. bulk action name or extra context.',
    )
    timestamp    = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'utils'
        ordering = ['-timestamp']
        verbose_name = 'audit log entry'
        verbose_name_plural = 'audit log entries'

    def __str__(self):
        model_name = self.content_type.model if self.content_type else 'unknown'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor} {self.action} {model_name} #{self.object_id}'

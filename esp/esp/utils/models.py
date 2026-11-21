from __future__ import absolute_import
from __future__ import unicode_literals
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

import os
import secrets
import time

from django.conf import settings
from django.core.files.storage import FileSystemStorage
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

    def __str__(self):
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

class PrinterQuerySet(models.QuerySet):
    def active(self):
        """ Locations in use (not archived). """
        return self.filter(archived=False)


#   Crockford base32, lowercased (CUPS queue names are case-insensitive)
ULID_ALPHABET = '0123456789abcdefghjkmnpqrstvwxyz'


def new_ulid():
    """ A ULID (https://github.com/ulid/spec): 48 bits of milliseconds then
    80 random bits, as 26 base32 characters, so ids sort by creation time.
    Keep this import path: migrations refer to it. """
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    return ''.join(ULID_ALPHABET[(value >> (5 * i)) & 31] for i in reversed(range(26)))


class Printer(models.Model):
    """ A place that prints on the day of the program ("Troubleshooting",
    "Help desk", "Check-in A"). At most one printer is connected to it at a
    time: a laptop running the printing page (with any printer installed on
    it, e.g. by USB), or a network printer the server sends jobs to over IPP.
    The Default location takes print requests that don't name a location,
    and also those of any location with nothing connected. """
    MODE_CHOICES = (
        ('none', 'Nothing connected'),
        ('laptop', 'Laptop'),
        ('network', 'Network printer'),
    )
    name = models.CharField(max_length=255, help_text='Name to display in onsite interface')
    printer_type = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_default = models.BooleanField(default=False, editable=False)
    #   Network printer: names this connection's queue on the print server
    #   (esp-<queue_id>), a new ULID for each connection, so unique across
    #   every site sharing the print server (unlike the id). None otherwise.
    queue_id = models.CharField(max_length=26, unique=True, null=True, blank=True, editable=False)
    #   Archived locations are hidden everywhere but keep their history and
    #   old print requests (the Printers page's "Archive" instead of deleting)
    archived = models.BooleanField(default=False)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='none')
    #   Network printer: what was typed, the ipp:// URI it means, what the
    #   printer said it supports (JSON), and the chosen settings (JSON)
    network_address = models.CharField(max_length=255, blank=True, default='')
    network_uri = models.CharField(max_length=255, blank=True, default='')
    network_info = models.TextField(blank=True, default='')
    settings_json = models.TextField(blank=True, default='')
    #   Laptop: who has it, and when it last asked for jobs
    laptop_token = models.CharField(max_length=64, blank=True, default='')
    laptop_claimed_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    laptop_last_seen = models.DateTimeField(blank=True, null=True)
    #   How the last job (or test) went
    last_result = models.CharField(max_length=20, blank=True, default='')
    last_result_at = models.DateTimeField(blank=True, null=True)
    last_error = models.TextField(blank=True, default='')
    #   Network printer: what is stopping jobs (print server unreachable, the
    #   printer not responding or out of paper...) and since when; blank when
    #   all is well
    trouble = models.TextField(blank=True, default='')
    trouble_since = models.DateTimeField(blank=True, null=True)

    objects = PrinterQuerySet.as_manager()

    def __str__(self):
        return self.name

class PrinterChange(models.Model):
    """ What happened to a location's printer connection, for its history. """
    printer = models.ForeignKey(Printer, on_delete=models.CASCADE, related_name='changes')
    action = models.CharField(max_length=40)
    detail = models.TextField(blank=True, default='')
    recorded_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-id',)

class PrintUploadStorage(FileSystemStorage):
    """ Where PDFs uploaded for printing (/manage/printpdf) are kept:
    settings.PRINT_UPLOAD_DIR, outside MEDIA_ROOT, which is served publicly.
    Read when used (not cached, so tests can override it), so migrations
    record only this class. Keep this import path: migrations refer to it. """

    @property
    def base_location(self):
        return settings.PRINT_UPLOAD_DIR

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def __eq__(self, other):
        return isinstance(other, PrintUploadStorage)

    def __hash__(self):
        return hash(PrintUploadStorage)


class PrintRequest(models.Model):
    KIND_CHOICES = (
        ('schedule', 'Student schedule'),
        ('receipt', 'Receipt'),
        ('pdf', 'Uploaded PDF'),
    )
    STATUS_CHOICES = (
        ('queued', 'Waiting to print'),
        ('sent', 'Sent to the printer'),
        ('printed', 'Printed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    printer = models.ForeignKey(Printer, blank=True, null=True)     #   Blank means the Default location.
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='schedule')
    program = models.ForeignKey('program.Program', blank=True, null=True, on_delete=models.CASCADE)
    #   What to print: a student's schedule, a receipt, or an uploaded PDF
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    receipt = models.ForeignKey('accounting.Receipt', blank=True, null=True, on_delete=models.CASCADE)
    file = models.FileField(upload_to='%Y/%m/', storage=PrintUploadStorage(), blank=True, null=True)
    copies = models.PositiveIntegerField(default=1)
    #   Settings for this job (JSON, like Printer.settings_json) over the
    #   printing location's own; those its printer can't do are skipped
    settings_json = models.TextField(blank=True, default='')
    title = models.CharField(max_length=200, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', db_index=True)
    error = models.TextField(blank=True, default='')
    attempts = models.PositiveIntegerField(default=0)
    #   A network job's id in the print server's CUPS (e.g. esp-01jd3k8w6p0b2c4d5e6f7g8h9j-12)
    #   while it is 'sent', until CUPS says it printed
    server_job = models.CharField(max_length=100, blank=True, default='')
    requested_by = AjaxForeignKey(ESPUser, blank=True, null=True, related_name='+', on_delete=models.SET_NULL)
    time_requested = models.DateTimeField(auto_now_add=True)
    time_executed = models.DateTimeField(blank=True, null=True)

    def describe(self):
        if self.title:
            return self.title
        if self.kind == 'schedule' and self.user_id:
            return 'Schedule for %s' % self.user.name()
        if self.kind == 'receipt' and self.receipt_id:
            return 'Receipt %d' % self.receipt.number
        return self.get_kind_display()

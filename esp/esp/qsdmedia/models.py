
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from django.conf import settings
from esp.db.fields import AjaxForeignKey
import os.path
from esp.middleware import ESPError

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# Create your models here.

# The folder that Media files are saved to
root_file_path = "uploaded"

class Media(models.Model):
    """ A generic container for 'media': videos, pictures, papers, etc. """
    friendly_name = models.TextField() # Human-readable description of the media
    target_file = models.FileField(upload_to=root_file_path) # Target media file
    size = models.IntegerField(blank=True, null=True, editable=False) # Size of the file, in bytes
    format = models.TextField(blank=True, null=True)  # Format string; should be human-readable (string format is currently unspecified)
    mime_type = models.CharField(blank=True, null=True, max_length=256, editable=False)
    file_extension = models.TextField(blank=True, null=True, max_length=16, editable=False) # Windows file extension for this file type, in case it's something archaic / Windows-centric enough to not get a unique MIME type
    file_name = models.TextField(blank=True, null=True, max_length=256, editable=False) # original filename that this file should be downloaded as
    hashed_name = models.TextField(blank=True, null=True, max_length=256, editable=False) # randomized filename

    #   Generic Foreign Key to object this media is associated with.
    #   Currently limited to be either a ClassSubject or Program.
    owner_type = models.ForeignKey(ContentType, blank=True, null=True, limit_choices_to={'model__in': ['classsubject', 'program']})
    owner_id = models.PositiveIntegerField(blank=True, null=True)
    owner = GenericForeignKey(ct_field='owner_type', fk_field='owner_id')

    def handle_file(self, file, filename):
        """ Saves a file from request.FILES. """
        import uuid

        # Do we actually need this?
        splitname = os.path.basename(filename).split('.')
        if len(splitname) > 1:
            self.file_extension = splitname[-1]
        else:
            self.file_extension = ''

        # get list of allowed file extensions
        if hasattr(settings, 'ALLOWED_EXTENSIONS'):
            allowed_extensions = [x.lower() for x in settings.ALLOWED_EXTENSIONS]
        else:
            allowed_extensions = ['pdf', 'odt', 'odp', 'jpg', 'jpeg', 'gif', 'png', 'doc', 'docx', 'ppt', 'pptx', 'zip', 'txt']

        if not self.file_extension.lower() in allowed_extensions:
            raise ESPError("The file extension provided is not allowed. Allowed extensions: %s." % (', '.join(allowed_extensions),), log=False)

        self.mime_type = file.content_type
        self.size = file.size

        # hash the filename, easy way to prevent bad filename attacks
        self.file_name = filename
        self.hashed_name = str(uuid.uuid4())

        while not self.test_upload_filename():
            self.hashed_name = str(uuid.uuid4())

        self.target_file.save(self.hashed_name, file)

    # returns an absolute path to this file
    def get_uploaded_filename(self):
        return os.path.join(settings.MEDIA_ROOT, "..", self.target_file.url.lstrip('/'))

    # returns an absolute path to this file
    def test_upload_filename(self):
        return not os.path.isfile(os.path.join(settings.MEDIA_ROOT, root_file_path, self.hashed_name))

    def delete(self, *args, **kwargs):
        """ Delete entry; provide hack to fix old absolute-path-storing. """
        import os
        if os.path.isfile(self.get_uploaded_filename()):
            os.remove(self.get_uploaded_filename())

        super(Media, self).delete(*args, **kwargs)

    def __unicode__(self):
        return unicode(self.friendly_name)

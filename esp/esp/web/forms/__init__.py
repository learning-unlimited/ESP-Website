
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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
""" ESP In-house Form Fields ... some of these might be useful
    ouside ESP.
    """

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile

class ResizeImageField(forms.ImageField):
    """ This field will allow one to upload a file, and that image
    to have a size to be resized to. """

    def __init__(self, size=None, **kwargs):
        """ Give this a tuple size, like (128,128), and the image
            will be resized so that it is no larger than that box, but
            its aspect ratio is preserved. """

        forms.ImageField.__init__(self, **kwargs)
        self.size = size

    def clean(self, file, initial=None):
        """ gets the image and resizes it """
        file = super(forms.ImageField, self).clean(file, initial)
        if file and self.size is not None:
            from PIL import Image
            from cStringIO import StringIO

            filename = file.name

            picturefile = StringIO()
            if hasattr(file, 'temporary_file_path'):
                file = file.temporary_file_path()
            #   Check that there was indeed something submitted.  Otherwise give up.
            elif hasattr(file, 'read'):
                file = StringIO(file.read())
            else:
                raise forms.ValidationError('Image unreadable.')

            try:
                im = Image.open(file)
                im.thumbnail(self.size, Image.ANTIALIAS)
                im.save(picturefile, im.format)
            except IOError:
                raise forms.ValidationError('Image resize failed.')

            picturefile.seek(0)
            file = SimpleUploadedFile(
                name=filename,
                content=picturefile.getvalue(),
                )
        return file


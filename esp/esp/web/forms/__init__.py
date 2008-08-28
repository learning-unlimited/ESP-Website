
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
""" ESP In-house Form Fields ... some of these might be useful
    ouside ESP.
    """

from django import oldforms as forms
from django.core.files.uploadedfile import SimpleUploadedFile

class ResizeImageUploadField(forms.ImageUploadField):
    """ This field will allow one to upload a file, and that image
    to have a size to be resized to. """

    def __init__(self, size=None, *args, **kwargs):
        """ Give this a tuple size, like (128,128), and the image
            will be resized so that it is no larger than that box, but
            its aspect ratio is preserved. """
        
        forms.ImageUploadField.__init__(self, *args, **kwargs)
        self.size = size
        
    def prepare(self, new_data):
        """ gets the image and resizes it """
        if self.size is not None:
            from PIL import Image
            from cStringIO import StringIO
            
            try:
                file = new_data[self.field_name]
            except KeyError:
                return new_data

            picturefile = StringIO()
            if hasattr(file, 'temporary_file_path'):
                file = file.temporary_file_path()
            #   Check that there was indeed something submitted.  Otherwise give up.
            elif hasattr(file, 'read'):
                file = StringIO(file.read())
            else:
                return new_data
            
            try:
                im = Image.open(file)
                im.thumbnail(self.size, Image.ANTIALIAS)
                im.save(picturefile, im.format)
            except IOError:
                return new_data

            picturefile.seek(0)
            new_data[self.field_name] = SimpleUploadedFile(
                name=new_data[self.field_name].name,
                content=picturefile.getvalue(),
                )

        return new_data


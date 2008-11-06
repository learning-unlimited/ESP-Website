
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
from django.db   import models
from django.conf import settings
from django.core.files.storage import default_storage

from esp.middleware   import ESPError
import os
import datetime
import md5

IMAGE_TYPE = 'png'

class SubSectionImage(models.Model):

    create_ts = models.DateTimeField(default = datetime.datetime.now,
                                     editable = False)
    text  = models.TextField(unique=True)
    image = models.ImageField(upload_to = 'subsection_images')
    font_size = models.IntegerField(default = 24)
    height = models.PositiveIntegerField(blank=True,null=True)
    width = models.PositiveIntegerField(blank=True, null=True)


    class Admin:
        pass

    def create_image(self):
        """
        Takes a string and creates a pretty image.
        """

        FONT = settings.MEDIA_ROOT + 'BOOKOS.TTF'

        font = ImageFont.truetype(FONT, self.font_size)

        font_string = self.text

        dim = font.getsize(font_string)

        dim = (350, dim[1],)

        im = Image.new('RGB',dim, 'white')
        draw = ImageDraw.Draw(im)

        draw.text((0,0),font_string, font=font, fill="#333333") #, fill=self.color)

        del draw

        im = im.rotate(270)
        im = im.filter(ImageFilter.SMOOTH)
        im = im.filter(ImageFilter.SHARPEN)        

        file_name = md5.new(font_string).hexdigest()

        full_file_name = '%s/%s/%s.%s' %\
                      (settings.MEDIA_ROOT, self._meta.get_field('image').upload_to, file_name, IMAGE_TYPE)
        part_file_name = '%s/%s.%s' % (self._meta.get_field('image').upload_to, file_name, IMAGE_TYPE)

        file = default_storage.open(full_file_name, 'wb')
        im.save(file, IMAGE_TYPE) 
        file.close()

        self.image = part_file_name
        
        models.Model.save(self)

        self.width, self.height = dim

    def save(self, *args, **kwargs):
        self.create_image()
        models.Model.save(self, *args, **kwargs)

    def __unicode__(self):
        if not os.path.exists(self.image.path):
            self.create_image()
        return '<img src="%s" alt="%s" border="0" title="%s" class="subsection" />' % (str(self.image.url), self.text, self.text)
        

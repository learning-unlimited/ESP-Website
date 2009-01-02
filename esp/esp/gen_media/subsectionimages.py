""" Image generation for subsection images at the side. """
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

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

from django.conf import settings
from esp.gen_media.base import GenImageBase

__all__ = ['SubSectionImage']


### FIXME: GenImageBase needs to provide arbitrary attributes... namely class
class SubSectionImage(GenImageBase):
    """ A generated LaTeX image for use in inlining. """

    DIR = 'subsection_images'
    EXT = 'png'

    def __init__(self, text, font_size=24, fill='#333333'):
        self.text = text
        self.font_size = font_size
        self.fill = fill
        super(SubSectionImage, self).__init__(text, font_size)

    @property
    def _alt(self):
        """ Define a proper alt string. """
        return self.text

    def _key(self):
        """ image key """
        return str(self.font_size) + '|' + self.text + '|' + self.fill

    def _generate_file(self):
        """ Generates the png file. """

        import ImageFont, Image, ImageDraw, ImageFilter

        font_path = settings.MEDIA_ROOT + 'BOOKOS.TTF'
        font = ImageFont.truetype(font_path, self.font_size)
        font_string = self.text

        dim = font.getsize(font_string)
        dim = (350, dim[1],)

        image = Image.new('RGB', dim, 'white')

        draw = ImageDraw.Draw(image)
        draw.text((0, 0), font_string, font=font, fill=self.fill)
        del draw

        image = image.rotate(270)
        image = image.filter(ImageFilter.SMOOTH)
        image = image.filter(ImageFilter.SHARPEN)

        from django.core.files.storage import default_storage
        output = default_storage.open(self.local_path, 'wb')
        image.save(output, self.EXT)
        output.close()

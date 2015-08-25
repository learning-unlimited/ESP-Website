""" Image generation for subsection images at the side. """
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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

from django.conf import settings
from esp.gen_media.base import GenImageBase

__all__ = ['EmailImage']


class EmailImage(GenImageBase):
    """ A generated LaTeX image for use in inlining. """

    DIR = 'email_images'
    EXT = 'png'

    def __init__(self, address, font_size=12, fill='#000000'):
        self.address = address
        self.font_size = font_size
        self.fill = fill
        super(EmailImage, self).__init__(address, font_size, fill)

    def _alt(self):
        """ Define a proper alt string. """
        return 'Email hidden for privacy'

    def _title(self):
        return ''

    def _key(self):
        """ image key """
        return str(self.font_size) + '|' + self.address + '|' + self.fill

    def _generate_file(self):
        """ Generates the png file. """

        from PIL import ImageFont, Image, ImageDraw, ImageFilter

        font_path = settings.MEDIA_ROOT + 'DroidSansMono.ttf'
        font = ImageFont.truetype(font_path, self.font_size)

        dim = font.getsize(self.address)

        image = Image.new('RGBA', dim, (255,255,255,0))

        draw = ImageDraw.Draw(image)
        draw.text((0, 0), self.address, font=font, fill=self.fill)
        del draw

        from django.core.files.storage import default_storage
        output = default_storage.open(self.local_path, 'wb')
        image.save(output, self.EXT)
        output.close()

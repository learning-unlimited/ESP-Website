
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
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.storage import FileSystemStorage

from esp.users.models import User
from esp.middleware   import ESPError
from django.core.files import File
import os
import datetime
import cStringIO as StringIO
import md5
from PIL import Image, ImageFont, ImageDraw, ImageFilter

TEXIMAGE_BASE = settings.MEDIA_ROOT + 'latex/'
TEXIMAGE_URL  = settings.MEDIA_URL + 'latex/'
IMAGE_TYPE    = 'png'
LATEX_DPI     = 150
LATEX_BG      = 'Transparent' #'white'

mimes         = {'gif': 'image/gif',
                 'png': 'image/png'}

commands = {'latex'  : '/usr/bin/latex',
            'dvips'  : '/usr/bin/dvips',
            'convert': '/usr/bin/convert',
            'dvipng' : '/usr/bin/dvipng'}

TMP      = '/tmp'

class LatexImage(models.Model):

    content  = models.TextField()
    image    = models.FileField(upload_to = 'latex')
    dpi      = models.IntegerField(blank=True, null=True)
    style    = models.CharField(max_length=16, choices = (('INLINE','INLINE'),('DISPLAY','DISPLAY')))
    filetype = models.CharField(max_length=10)

    def getImage(self):
        if self.genImage():
            return str(self)
        else:
            return self.content.strip('$')

    def genImage(self):

        if self.file_exists():
            return True
        
        if not self.image:
            file_base = get_rand_file_base()
            self.filetype = IMAGE_TYPE
        else:
            #   Get the filename without its extension
            file_base = os.path.basename(self.image.path)

        if self.style == 'INLINE':
            style = '$'
        elif self.style == 'DISPLAY':
            style = '$$'
        else:
            raise ESPError(False), 'Unknown display style'

        tex = r"""\documentclass[fleqn]{article} \usepackage{amssymb,amsmath} """ +\
              r"""\usepackage[latin1]{inputenc} \begin{document} """ + \
              r""" \thispagestyle{empty} \mathindent0cm \parindent0cm %s%s%s \end{document}""" % \
              (style, self.content, style)

        tmppath = TMP + '/' + file_base
    
        tex_file = open(tmppath + '.tex', 'w')
        tex_file.write(tex)
        tex_file.close()

        if self.dpi is None:
            cur_dpi = LATEX_DPI
        else:
            cur_dpi = self.dpi

        os.system('cd %s && %s -interaction=nonstopmode %s > /dev/null' % \
                  (TMP, commands['latex'], tmppath))

        os.system( '%s -q -T tight -bg %s -D %s -o %s.png %s.dvi > /dev/null' % \
                  (commands['dvipng'], LATEX_BG, cur_dpi, TEXIMAGE_BASE + file_base, tmppath))

        if self.filetype.lower() != 'png':
            os.system( '%s %s.png %s.%s %> /dev/null' % \
                       (commands['convert'], TEXIMAGE_BASE + file_base, TEXIMAGE_BASE + file_base, self.filetype))
        
        #   Read the image file data
        img_file = open(TEXIMAGE_BASE + file_base + '.' + self.filetype)
        
        #   Save it to a Django file
        fs = FileSystemStorage(location=TEXIMAGE_BASE, base_url=TEXIMAGE_URL)
        self.image = fs.save('latex/' + file_base + '.' + self.filetype, File(img_file))
    
        img_file.close()
        
        self.save(super=True)
        
        return True

    def save(self, *args, **kwargs):
        if 'super' not in kwargs:
            self.genImage()
        else:
            del kwargs['super']
        super(LatexImage,self).save(*args, **kwargs)
        

    def __str__(self):
        return '<img src="%s" alt="%s" title="%s" border="0" class="LaTeX" align="middle" />' % \
               (self.image.url, self.content, self.content)
        
    def file_exists(self):
        if not self.image:
            return False
        return os.path.exists(self.image.path)

    class Admin:
        pass
    
def get_rand_file_base():
    import sha
    from random import random

    rand = sha.new(str(random())).hexdigest()

    while os.path.exists('%s/%s.%s' % (TEXIMAGE_BASE, rand, IMAGE_TYPE)):
        rand = sha.new(str(random())).hexdigest()
    return rand

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

    def __str__(self):
        if not os.path.exists(self.image.path):
            self.create_image()
        return '<img src="%s" alt="%s" border="0" title="%s" class="subsection" />' % (str(self.image.url), self.text, self.text)
        

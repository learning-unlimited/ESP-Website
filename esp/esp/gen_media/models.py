
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
from esp.users.models import User
from esp.middleware   import ESPError
import os

TEXIMAGE_BASE = settings.MEDIA_ROOT+'/latex'
TEXIMAGE_URL  = '/media/uploaded/latex'
IMAGE_TYPE    = 'png'
LATEX_DPI     = 150
LATEX_BG      = 'Transparent' #'white'

mimes         = {'gif': 'image/gif',
                 'png': 'image/png'}

commands = {'latex'  : 'openin_any=p /usr/bin/latex',
            'dvips'  : '/usr/bin/dvips',
            'convert': '/usr/bin/convert',
            'dvipng' : '/usr/bin/dvipng'}

TMP      = '/tmp'

class LatexImage(models.Model):

    content  = models.TextField()
    filename = models.TextField()
    dpi      = models.IntegerField(blank=True, null=True)
    style    = models.CharField(maxlength=16, choices = (('INLINE','INLINE'),('DISPLAY','DISPLAY')))
    filetype = models.CharField(maxlength=10)

    def getImage(self):
        if not self.file_exists():
            self.genImage()
            self.save()
        return str(self)

    def genImage(self):
        if not self.filename:
            self.filename = get_rand_file_base()
            self.filetype = IMAGE_TYPE


        if self.style == 'INLINE':
            style = '$'
        elif self.style == 'DISPLAY':
            style = '$$'
        else:
            raise ESPError(False), 'Unknown display style'

            
        tex = r"""\documentclass[fleqn]{article} \usepackage{amssymb,amsmath} """ +\
              r"""\usepackage[latin1]{inputenc} \begin{document} \\""" + \
              r""" \thispagestyle{empty} \mathindent0cm \parindent0cm %s%s%s \end{document}""" % \
              (style, self.content, style)

        fullpath = TMP+'/'+self.filename

        tex_file = open(fullpath + '.tex', 'w')
        tex_file.write(tex)
        tex_file.close()

        if self.dpi is None:
            cur_dpi = LATEX_DPI
        else:
            cur_dpi = self.dpi

        os.system('cd %s; %s -interaction=nonstopmode %s &>/dev/null' % \
                  (TMP, commands['latex'], self.filename))

        os.system( '%s -q -T tight -bg %s -D %s -o %s.png %s.dvi &&  %s %s.png %s/%s.%s &> /dev/null' % \
                  (commands['dvipng'], LATEX_BG, cur_dpi, fullpath, fullpath, commands['convert'], fullpath,
                   TEXIMAGE_BASE, self.filename, self.filetype))

        os.system('rm -f %s/%s*' % (TMP, self.filename))
        
        return True
        

    def __str__(self):
        return '<img src="%s/%s.%s" alt="%s" title="%s" border="0" class="LaTeX" align="middle" />' % \
               (TEXIMAGE_URL, self.filename, self.filetype, self.content, self.content)
        

    def file_exists(self):
        
        if not self.filename:
            return False

        return os.path.exists('%s/%s.%s' % (TEXIMAGE_BASE, self.filename, self.filetype))
    
def get_rand_file_base():
    import sha
    from random import random

    rand = sha.new(str(random())).hexdigest()

    while os.path.exists('%s/%s.%s' % (TEXIMAGE_BASE, rand, IMAGE_TYPE)):
        rand = sha.new(str(random())).hexdigest()

   
    return rand




    


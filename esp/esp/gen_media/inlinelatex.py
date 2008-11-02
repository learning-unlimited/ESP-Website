
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 MIT ESP

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
from esp.middleware import ESPError

import tempfile
import sha
import os

__all__ = ['InlineLatex']

TMP      = tempfile.gettempdir()

TEXIMAGE_DIR = 'latex'
IMAGE_TYPE    = 'png'
LATEX_DPI     = 150
LATEX_BG      = 'Transparent' #'white'

commands = {'latex'  : '/usr/bin/latex',
            'dvips'  : '/usr/bin/dvips',
            'convert': '/usr/bin/convert',
            'dvipng' : '/usr/bin/dvipng'}

class InlineLatex(object):
    def __init__(self, content, style='DISPLAY', dpi=LATEX_DPI):
        self.content = content
        self.style = style
        self.dpi = dpi

        self.file_base = sha.sha(style + '|' + str(dpi) + '|' + content).hexdigest()
        self.file_name = self.file_base + '.' + IMAGE_TYPE

        # Avoid having too many files in a single directory
        # (git does this too. :D And mediawiki does something similar.)
        dir = self.file_name[:2]
        self.file_name = self.file_name[2:]
        self.file_path = os.path.join(TEXIMAGE_DIR, dir, self.file_name)

        self._generate_file()

    def local_path(self):
        """ The path to the file on the filesystem. """
        return os.path.join(settings.MEDIA_ROOT, self.file_path)

    def url(self):
        """ The URL of the file. """
        # FIXME: Windoze?
        return os.path.join(settings.MEDIA_URL, self.file_path)

    def img(self):
        """ An image tag, ready to be inserted into HTML. """
        return '<img src="%s" alt="%s" title="%s" border="0" class="LaTeX" align="middle" />' \
                % (self.url(), self.content, self.content)

    def _generate_file(self):
        """ Generates the png file. """

        if not os.path.exists(self.file_path):
            # Make directory if it doesn't exist
            dir = os.path.dirname(self.local_path())
            if not os.path.exists(dir):
                os.mkdir(dir)

            if self.style == 'INLINE':
                math_style = '$'
            elif self.style == 'DISPLAY':
                math_style = '$$'
            else:
                raise ESPError(False), 'Unknown display style'

            tex = r"""\documentclass[fleqn]{article} \usepackage{amssymb,amsmath} """ +\
                  r"""\usepackage[latin1]{inputenc} \begin{document} """ + \
                  r""" \thispagestyle{empty} \mathindent0cm \parindent0cm %s%s%s \end{document}""" % \
                  (math_style, self.content, math_style)

            tmppath = os.path.join(TMP, self.file_base)

            tex_file = open(tmppath + '.tex', 'w')
            tex_file.write(tex.encode('utf-8'))
            tex_file.close()

            if os.system('cd %s && %s -interaction=nonstopmode %s > /dev/null' % \
                    (TMP, commands['latex'], tmppath)) is not 0:
                raise ESPError(False), 'latex compilation failed.'

            if os.system( '%s -q -T tight -bg %s -D %s -o %s %s.dvi > /dev/null' % \
                    (commands['dvipng'], LATEX_BG, self.dpi, self.local_path(), tmppath)) is not 0:
                raise ESPError(False), 'dvipng failed.'

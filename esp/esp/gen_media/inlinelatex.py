
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
from esp.middleware import ESPError
from esp.gen_media.base import GenImageBase

import tempfile
import os

__all__ = ['InlineLatex']

TMP      = tempfile.gettempdir()

LATEX_DPI     = 150
LATEX_BG      = 'Transparent' #'white'

COMMANDS = {'latex'  : '/usr/bin/latex',
            'dvips'  : '/usr/bin/dvips',
            'convert': '/usr/bin/convert',
            'dvipng' : '/usr/bin/dvipng'}

class InlineLatex(GenImageBase):
    """ A generated LaTeX image for use in inlining. """

    DIR = 'latex'
    EXT = 'png'

    def __init__(self, content, style='DISPLAY', dpi=LATEX_DPI):
        self.content = content
        self.style = style
        self.dpi = dpi
        super(InlineLatex, self).__init__(content, style, dpi)

    @property
    def _alt(self):
        return self.content

    def _key(self):
        return self.style + '|' + str(self.dpi) + '|' + self.content

    def _generate_file(self, *args, **kwargs):
        """ Generates the png file. """

        if self.style == 'INLINE':
            math_style = '$'
        elif self.style == 'DISPLAY':
            math_style = '$$'
        else:
            raise ESPError(False), 'Unknown display style'

        tex = r"\documentclass[fleqn]{article} \usepackage{amssymb,amsmath} " +\
              r"\usepackage[latin1]{inputenc} \begin{document} " + \
              r" \thispagestyle{empty} \mathindent0cm \parindent0cm %s%s%s \end{document}" % \
              (math_style, self.content, math_style)

        tmppath = os.path.join(TMP, self.file_base)

        tex_file = open(tmppath + '.tex', 'w')
        tex_file.write(tex.encode('utf-8'))
        tex_file.close()

        if os.system('cd %s && %s -interaction=nonstopmode %s > /dev/null' % \
                (TMP, COMMANDS['latex'], tmppath)) is not 0:
            raise ESPError(False), 'latex compilation failed.'

        if os.system( '%s -q -T tight -bg %s -D %s -o %s %s.dvi > /dev/null' % \
                (COMMANDS['dvipng'], LATEX_BG, self.dpi, self.local_path, tmppath)) is not 0:
            raise ESPError(False), 'dvipng failed.'

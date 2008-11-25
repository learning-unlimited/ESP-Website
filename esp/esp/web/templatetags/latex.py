""" ESP Custom Filters for template """

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

from django import template
from esp.gen_media.inlinelatex import InlineLatex
from django.utils.encoding import force_unicode
register = template.Library()

@register.filter
def texescape(value):
    """ This will escape a string according to the rules of LaTeX """

    value = unicode(value).strip()

    special_backslash = '!**ABCDEF**!' # something unlikely to be repeated


    # we will make escape all the strings except those sandwiched between
    # $$ and $$. Thus you can write math symbols like $$\sqrt{3}$$ and
    # get away with it.
    strings = value.split('$$')
    for i in range(len(strings)):
        if i % 2 == 1 and i < len(strings) - 1:
            continue
        strings[i] = strings[i].replace('\\', special_backslash)
        for char in '&$%#_{}':
            strings[i] = strings[i].replace(char, '\\' + char)
        strings[i] = strings[i].replace(special_backslash, '$\\backslash$')
    

    value = '$'.join(strings)


    # now we have to make quotes pretty...
    strings = value.split('"')

    value = strings[0]
    for i in range(1, len(strings)):
        if i % 2 == 1:
            value += '``' + strings[i]
        else:
            value += "''" + strings[i]

    # deal with new-lines and a couple other oddities
    value = value.replace('[', '(')
    value = value.replace(']', ')')
    value = value.replace('\r\n', '\n')
    value = value.replace('\r',   '\n')
    value = value.replace('\n',   '\\\\\n')

    value = value.encode('ascii', 'ignore')

    return value

@register.filter
def teximages(value, dpi=150):
    """ Parse string for "$$foo$$", replace with inline LaTeX image, at
    the specified DPI, defauting to 150. """

    value = force_unicode(value, errors='replace').strip()

    strings = value.split('$$')
    style   = 'DISPLAY'

    converted = [ False for i in range(len(strings)) ]

    for i in range(len(strings)):
        if i % 2 == 1 and i < len(strings) - 1:
            if len(strings[i].strip()) > 0:
                try:
                    latex = InlineLatex(strings[i], style=style, dpi=dpi)
                    strings[i] = latex.img
                    converted[i] = True
                except:
                    converted[i] = False

    value = strings[0]

    for i in range(1, len(strings)):
        if converted[i] or converted[i-1]:
            value += strings[i]
        else:
            value += '$$' + strings[i]
        
    return value
teximages.is_safe = True





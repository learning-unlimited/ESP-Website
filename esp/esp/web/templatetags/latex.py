""" ESP Custom Filters for template """

__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from django import template
from django.utils.encoding import force_unicode
register = template.Library()

@register.filter
def texescape(value):
    """ This will escape a string according to the rules of LaTeX """

    value = unicode(value).strip()



    # we will make escape all the strings except those sandwiched between
    # $$ and $$. Thus you can write math symbols like $$\sqrt{3}$$ and
    # get away with it.
    strings = value.split('$$')

    # But not if we don't have something of the form "asdf $$ fghj $$ hjkl"; then someone's just messing with us
    if len(strings) % 2 == 0:
        strings = [ value ]

    replacement_pairs=[
            ('\\', r'!++ABCDEF++!'),
    ]
    for char in '&$%#_{}':
        replacement_pairs.append((char,'\\'+char))
    replacement_pairs.extend([
    ('^' , r'\textasciicircum{}'),
    ('>' , r'\textgreater{}'),
    ('<' , r'\textless{}'),
    ('~' , r'\ensuremath{\sim}'),
    (r'!++ABCDEF++!',r'\textbackslash{}'),
    ])

    for i in range(len(strings)):
        if i % 2 == 1 and i < len(strings) - 1:
            continue
        for key , val in replacement_pairs:
            strings[i] = strings[i].replace(key,val)

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
    value = value.replace('\n',   '~\\\\\n')

    value = value.encode('ascii', 'ignore')

    return value






__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 MIT ESP

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
from django.template.defaultfilters import stringfilter

from esp.tagdict.models import Tag
    
register = template.Library()

class OverrideNode(template.Node):
    def __init__(self, nodelist, format_string, *args):
        self.format_string = format_string.strip('"').rstrip('"')
        self.args = args
        self.nodelist = nodelist
    def render(self, context):
        value = self.nodelist.render(context)
        arg_list = []
        log_msg = []
        for arg in self.args:
            log_msg.append('%s -- %s' % (arg, context))
            arg_list.append(arg.resolve(context))
        tag_key = self.format_string % tuple(arg_list)
        tags = Tag.objects.filter(key=tag_key).order_by('-id')
        if tags.count() > 0:
            return tags[0].value
        else:
            return value

class CommentNode(template.Node):
    def render(self, context):
        return ''
        
@register.tag
def end_check_override(parser, token):
    return CommentNode()

@register.tag
def check_override(parser, token):
    nodelist = parser.parse(('end_check_override',))
    parser.delete_first_token()
    try:
        arg_list = token.split_contents()
        tag_name = arg_list[0]
        format_string = arg_list[1]
        args = [template.Variable(arg) for arg in arg_list[2:]]
    except ValueError:
        raise template.TemplateSyntaxError, "Something went wrong in an override."

    return OverrideNode(nodelist, format_string, *args)



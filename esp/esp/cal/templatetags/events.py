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
  Email: web-team@lists.learningu.org
"""

import re
from django import template
from datetime import datetime
from esp.cal.models import Event
from esp.datatree.models import *
    
register = template.Library()
arg_re_num = re.compile('\s*(\S+)\s+(\S+)\s+(\d+)\s*')
arg_re     = re.compile('\s*(\S+)\s+(\S+)\s*')

@register.filter
def group_events(event_list):
    result = Event.group_contiguous(event_list)
    return [Event.collapse(sublist) for sublist in result]

class EventNode(template.Node):
    """ Template node for Events list, based on the equivalent for Miniblog """
    
    def __init__(self, event_type, tree_uri, limit = None):
        self.event_type = event_type
        self.tree_uri = tree_uri
        self.limit = limit

    def render(self, context):
        anchor_node = GetNode(self.tree_uri)
        queryset = Event.objects.filter(event_type__description=self.event_type, end__gte=datetime.now()).filter(QTree(anchor__below=anchor_node)).order_by('start')
        if self.limit:
            context['event_list'] = queryset[:self.limit]
        else:
            context['event_list'] = queryset
        return ''

@register.tag
def generate_event_list(parser, token):
    """
    Returns a list of event objects with a particular type description
    that are anchored beneath a particular node.
    
    Example:
        {% generate_event_list Announcement Q/Web 3 %}
      will return the last 3 events of type "Announcement" anchored at "Q/Web"
      or at any of its descendants.  Leave out the last argument to get no limit.
    """

    tag = token.contents.split()[0]
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % tag

    match = arg_re_num.match(arg)
    if match:
        event_type, tree_uri, limit = match.groups()
    else:
        limit = None
        match = arg_re.match(arg)
        if not match:
            raise template.TemplateSyntaxError, "%r tag requires at least two arguments" % tag
        event_type, tree_uri = match.groups()

    if limit:
        try:
            limit = int(limit)
        except ValueError:
            raise template.TemplateSyntaxError, "%s tag requires third argument to be an int" % tag

    return EventNode(event_type, tree_uri, limit)

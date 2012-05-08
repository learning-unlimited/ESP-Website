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

from django import template
from esp.program.models import ClassSection
from esp.resources.models import Resource
from esp.resources.templatetags.resources import matrix_td, color_needs
from esp.cache.key_set import wildcard
from esp.web.util.template import cache_inclusion_tag
    
register = template.Library()

@cache_inclusion_tag(register, 'inclusion/program/matrix_row.html')
def scheduling_matrix_row(room, program):
    #   Returns context needed for template.
    return  {   'room_name': room.name,
                'room_num_students': room.num_students,
                'room_associated_resources': [ar.res_type.name for ar in room.associated_resources()],
                'room_sequence': [matrix_td(elt) for elt in room.schedule_sequence(program)]
            }
scheduling_matrix_row.cached_function.depend_on_row(lambda: Resource, lambda r: {'room': r})
            
@cache_inclusion_tag(register, 'inclusion/program/class_options.html')
def class_options_row(cls):
    """ So it's no longer just one row.  This returns a block of rows for the scheduling table,
    one with information about the class and its teachers, and then one for setting the times
    and rooms of each section. """
    def prepare_section_dict(sec):
        context = {}
        
        context['code'] = sec.emailcode()
        context['id'] = sec.id
        context['index'] = sec.index()
        context['title'] = str(sec)
        total_minutes = sec.duration * 60
        hours = int(total_minutes / 60)
        minutes = total_minutes - hours * 60
        context['duration'] = '%d hr %d min' % (hours, minutes)
        context['scheduling_status'] = color_needs(sec.scheduling_status())
        context['start_time'] = sec.start_time()
        if context['start_time'] is None:
            context['start_time'] = {'id': -1}
        context['friendly_times'] = [ft for ft in sec.friendly_times()]
        context['viable_times'] = [{'id': vt.id, 'pretty_start_time': vt.pretty_start_time(), 'selected': ((sec.start_time() is not None) and (sec.start_time().id == vt.id))} for vt in sec.viable_times()]
        context['initial_rooms'] = [{'id': room.id, 'name': room.name, 'num_students': room.num_students, 'resources': [r.res_type.name for r in room.associated_resources()]} for room in sec.initial_rooms()]
        context['sufficient_length'] = sec.sufficient_length()
        context['students_actual'] = sec.num_students()
        context['students_max'] = sec.parent_class.class_size_max
        context['viable_rooms'] = sec.viable_rooms()
        
        return context
        
    context = {}

    context['cls'] = cls
    context['cls_high_school_only'] = (cls.grade_min >= 9)
    context['cls_id'] = cls.id
    context['cls_title'] = cls.anchor.friendly_name
    context['cls_code'] = cls.emailcode()
    context['cls_requests'] = [r.res_type.name for r in cls.default_section().getResourceRequests()]
    context['cls_teachers'] = [{'first_name': t.first_name, 'last_name': t.last_name, 'available_times': [e.short_time() for e in t.getAvailableTimes(cls.parent_program)]} for t in cls.teachers()]
    context['cls_prereqs'] = cls.prereqs
    context['cls_message'] = cls.message_for_directors
    context['cls_checkitems'] = [cm.title for cm in cls.checklist_progress.all()]
    
    context['cls_sections'] = [prepare_section_dict(s) for s in cls.sections.all()]

    return context
class_options_row.cached_function.depend_on_cache(lambda: ClassSection.scheduling_status, lambda cs=wildcard, **kwargs: {'cls': cs.parent_class})

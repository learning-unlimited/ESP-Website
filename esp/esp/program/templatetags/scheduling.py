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
from esp.resources.templatetags.resources import matrix_td, color_needs
from esp.web.util.template import cache_inclusion_tag
    
register = template.Library()

def schedule_key_func(room, program):
    chars_to_avoid = '~!@#$%^&*(){}_ :;,"\\?<>'
    clean_name = ''.join(c for c in room.name if c not in chars_to_avoid)
    return 'SCHEDMATRIX__%s_%s' % (clean_name, program.id)

def options_key_func(cls):
    return 'CLASSOPTIONS__%s' % cls.id

@cache_inclusion_tag(register, 'inclusion/program/matrix_row.html', cache_key_func=schedule_key_func)
def scheduling_matrix_row(room, program):
    #   Returns context needed for template.
    room.clear_schedule_cache(program)
    return  {   'room_name': room.name,
                'room_num_students': room.num_students,
                'room_associated_resources': [ar.res_type.name for ar in room.associated_resources()],
                'room_sequence': [matrix_td(elt) for elt in room.schedule_sequence(program)]
            }
            
@cache_inclusion_tag(register, 'inclusion/program/class_options.html', cache_key_func=options_key_func)
def class_options_row(cls):
    context = {}

    context['cls'] = cls
    context['cls_high_school_only'] = (cls.grade_min >= 9)
    context['cls_id'] = cls.id
    context['cls_title'] = cls.anchor.friendly_name
    context['cls_code'] = cls.emailcode()
    cls_total_minutes = cls.duration * 60
    cls_hours = int(cls_total_minutes / 60)
    cls_minutes = cls_total_minutes - cls_hours * 60
    context['cls_duration'] = '%d hr %d min' % (cls_hours, cls_minutes)
    context['cls_requests'] = [r.res_type.name for r in cls.getResourceRequests()]
    context['cls_teachers'] = [{'first_name': t.first_name, 'last_name': t.last_name} for t in cls.teachers()]
    context['cls_scheduling_status'] = color_needs(cls.scheduling_status())
    context['cls_start_time'] = cls.start_time()
    context['cls_friendly_times'] = [ft for ft in cls.friendly_times()]
    context['cls_viable_times'] = [{'id': vt.id, 'pretty_start_time': vt.pretty_start_time(), 'selected': ((cls.start_time() is not None) and (cls.start_time().id == vt.id))} for vt in cls.viable_times()]
    context['cls_initial_rooms'] = [{'id': room.id, 'name': room.name, 'num_students': room.num_students, 'resources': [r.res_type.name for r in room.associated_resources()]} for room in cls.initial_rooms()]
    context['cls_sufficient_length'] = cls.sufficient_length()
    context['cls_students_actual'] = cls.num_students()
    context['cls_students_max'] = cls.class_size_max
    context['cls_prereqs'] = cls.prereqs
    context['cls_message'] = cls.message_for_directors
    context['cls_viable_rooms'] = cls.viable_rooms()
    
    return context
    

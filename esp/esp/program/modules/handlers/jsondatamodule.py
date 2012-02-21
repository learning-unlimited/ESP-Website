
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.program.modules.base import ProgramModuleObj, CoreModule, needs_student, needs_teacher, needs_admin, needs_onsite, needs_account, main_call, aux_call

from esp.cal.models import Event
from esp.program.models import ClassSection, ClassSubject, StudentRegistration
from esp.resources.models import ResourceAssignment

from esp.cache.key_set import wildcard
from esp.utils.decorators import cached_module_view, json_response
from esp.utils.no_autocookie import disable_csrf_cookie_update

from django.views.decorators.cache import cache_control


class JSONDataModule(ProgramModuleObj, CoreModule):
    """ A program module dedicated to returning program-specific data in JSON form. """

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "JSON Data Module",
            "link_title": "JSON Data",
            "module_type": "json",
            "seq": 0,
            } ]

    """ Warning: for performance reasons, these views are not abstracted away from
        the models.  If the schema is changed this code will need to be updated.
    """
    
    @aux_call
    @json_response()
    @needs_admin
    @cached_module_view
    def counts(prog):
        return {'sections': list(ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog).values('id', 'enrolled_students'))}
    counts.method.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    counts.method.cached_function.depend_on_row(StudentRegistration, lambda sr: {'prog': sr.section.parent_class.parent_program})
    
    @aux_call
    @json_response({'resourceassignment__resource__name': 'name', 'resourceassignment__resource__num_students': 'num_students', 'resourceassignment__resource__event': 'timeslot'})
    @needs_admin
    @cached_module_view
    def rooms(prog):
        return {'rooms': list(ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog).select_related('resourceassignment__resource__name').values('id', 'resourceassignment__resource__name', 'resourceassignment__resource__num_students', 'resourceassignment__resource__event'))}
    rooms.method.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    rooms.method.cached_function.depend_on_row(ResourceAssignment, lambda ra: {'prog': ra.target.parent_class.parent_program})
    
    @aux_call
    @json_response({'resourceassignment__resource__name': 'room'})
    @needs_admin
    @cached_module_view
    def schedule_assignments(prog):
        data = ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog).select_related('resourceassignment__resource__name', 'resourceassignment__resource__event').extra({'timeslots': 'SELECT string_agg(to_char(resources_resource.event_id, \'999\'), \',\') FROM resources_resource, resources_resourceassignment WHERE resources_resource.id = resources_resourceassignment.resource_id AND resources_resourceassignment.target_id = program_classsection.id'}).values('id', 'resourceassignment__resource__name', 'timeslots').distinct()
        #   Convert comma-separated timeslot IDs to lists
        for i in range(len(data)):
            if data[i]['timeslots']:
                data[i]['timeslots'] = [int(x) for x in data[i]['timeslots'].strip().split(',')]
            else:
                data[i]['timeslots'] = []
        return {'sections': list(data)}
    schedule_assignments.method.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    schedule_assignments.method.cached_function.depend_on_row(ResourceAssignment, lambda ra: {'prog': ra.target.parent_class.parent_program})
    
    @aux_call
    @json_response()
    @cached_module_view
    def timeslots(prog):
        timeslots = list(prog.getTimeSlots().extra({'label': """to_char("start", 'Dy HH:MI -- ') || to_char("end", 'HH:MI AM')"""}).values('id', 'label', 'start', 'end'))
        for i in range(len(timeslots)):
            timeslot_start = Event.objects.get(pk=timeslots[i]['id']).start
            timeslots_before = Event.objects.filter(start__lt=timeslot_start)
            timeslots[i]['starting_sections'] = list(ClassSection.objects.exclude(meeting_times__in=timeslots_before).filter(meeting_times=timeslots[i]['id']).order_by('id').values_list('id', flat=True))
            timeslots[i]['sections'] = list(ClassSection.objects.filter(meeting_times=timeslots[i]['id']).order_by('id').values_list('id', flat=True))
            timeslots[i]['start'] = timeslots[i]['start'].timetuple()[:6]
            timeslots[i]['end'] = timeslots[i]['end'].timetuple()[:6]

        return {'timeslots': timeslots}
    timeslots.cached_function.depend_on_model(Event)
    timeslots.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})
        
    @aux_call
    @json_response({
            'parent_class__anchor__friendly_name': 'title',
            'parent_class__id': 'parent_class',
            'parent_class__anchor__name': 'emailcode',
            'parent_class__category__symbol': 'category',
            'parent_class__grade_max': 'grade_max',
            'parent_class__grade_min': 'grade_min',
            'enrolled_students': 'num_students'})
    @cached_module_view
    def sections(prog):
        sections = list(prog.sections().values(
                'id',
                'parent_class__anchor__friendly_name',
                'parent_class__id',
                'parent_class__category__symbol',
                'parent_class__anchor__name',
                'parent_class__grade_max',
                'parent_class__grade_min',
                'enrolled_students'))
        for section in sections:
            section['index'] = ClassSection.objects.get(id=section['id']).index()
        return {'sections': sections}
    sections.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    sections.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'prog': self.parent_program})
        
    @aux_call
    @json_response()
    @needs_student
    def lottery_preferences(self, request, tl, one, two, module, extra, prog):
        sections = list(prog.sections().values('id'))
        sections_interested = StudentRegistration.valid_objects().filter(relationship__name='Interested', user=request.user, section__parent_class__parent_program=prog).select_related('section__id').values_list('section__id', flat=True).distinct()
        sections_priority = StudentRegistration.valid_objects().filter(relationship__name='Priority/1', user=request.user, section__parent_class__parent_program=prog).select_related('section__id').values_list('section__id', flat=True).distinct()
        for item in sections:
            if item['id'] in sections_interested:
                item['lottery_interested'] = True
            else:
                item['lottery_interested'] = False
            if item['id'] in sections_priority:
                item['lottery_priority'] = True
            else:
                item['lottery_priority'] = False
        return {'sections': sections}
        
    @aux_call
    @cache_control(public=True, max_age=300)
    @json_response()
    #'category': 'category',
    #'class_info': 'class_info',
    #'difficulty': 'difficulty',
    #'emailcode': 'emailcode',
    #'prereqs': 'prereqs',
    #'sections': 'sections',
    #'teachers': 'teachers',
    #'title': 'title',
    #'first_name': 'first_name',
    #'last_name': 'last_name'

    def class_info(self, request, tl, one, two, module, extra, prog):
        if 'section_id' in request.GET:
            section_id = int(request.GET['section_id'])
            target_qs = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            class_id = int(request.GET['class_id'])
            target_qs = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError(False), 'Need a section or subject ID to fetch catalog info'
            
        matching_classes = ClassSubject.objects.catalog_cached(prog, initial_queryset=target_qs)
        assert(len(matching_classes) == 1)
        
        cls = matching_classes[0]
        cls_dict = {
            'id': cls.id,
            'emailcode': cls.emailcode(),
            'title': cls.title(),
            'class_info': cls.class_info, 
            'category': cls._category_cache.category, 
            'difficulty': cls.hardness_rating,
            'prereqs': cls.prereqs, 
            'sections': [x.id for x in cls._sections],
            'teachers': [x.id for x in cls._teachers],
        }
        teacher_list = [{'id': t.id, 'first_name': t.first_name, 'last\
_name': t.last_name} for t in cls._teachers]
        return {'classes': [cls_dict], 'teachers': teacher_list}
        
    class Meta:
        abstract = True

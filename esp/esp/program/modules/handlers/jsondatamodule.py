
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
from esp.program.modules.handlers.splashinfomodule import SplashInfoModule
from esp.program.modules.forms.splashinfo import SplashInfoForm
from esp.program.models import SplashInfo
from esp.users.models import UserAvailability
from esp.cal.models import Event
from esp.program.models import Program, ClassSection, ClassSubject, StudentRegistration, ClassCategories
from esp.program.models.class_ import open_class_category
from esp.resources.models import Resource, ResourceAssignment, ResourceRequest, ResourceType
from esp.datatree.models import *
from esp.dbmail.models import MessageRequest
from esp.tagdict.models import Tag

from esp.utils.decorators import cached_module_view, json_response
from esp.utils.no_autocookie import disable_csrf_cookie_update

from django.views.decorators.cache import cache_control
from django.db.models import Count, Sum
from django.db.models.query import Q

from collections import defaultdict
from datetime import datetime
import operator
import simplejson as json

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
    @json_response()
    @needs_admin
    @cached_module_view
    def rooms(prog):
        classrooms = prog.getResources().filter(res_type__name="Classroom")
        classrooms_grouped = defaultdict(list)

        for room in classrooms:
            classrooms_grouped[room.name].append(room)

        classrooms_dicts = [
            {
                'id': room_id,
                'uid': room_id,
                'text': classrooms_grouped[room_id][0].name,
                'availability': [ r.event_id for r in classrooms_grouped[room_id] ],
                'associated_resources': [ar.res_type.id for ar in classrooms_grouped[room_id][0].associated_resources()],
                'num_students': classrooms_grouped[room_id][0].num_students,
            } for room_id in classrooms_grouped.keys() ]

        return {'rooms': classrooms_dicts}
    rooms.method.cached_function.depend_on_model(lambda: Resource)

    @aux_call
    @json_response()
    @cached_module_view
    def resource_types(prog):
        res_types = ResourceType.objects.filter(program = prog)
        if len(res_types) == 0:
            res_types = ResourceType.objects.filter(program__isnull=True)

        res_types_dicts = [
            {
                'id': rt.id,
                'uid': rt.id,
                'name': rt.name,
                'description': rt.description,
                # Comment carried over from ajaxschedulingmodule.py -- gurtej 03/06/2012
                ## .attributes wasn't working properly; so just using this for now -- aseering 10/21/2010
                'attributes': rt.attributes_pickled.split("|"),
            }
            for rt in res_types ]

        return {'resource_types': res_types_dicts}
    resource_types.cached_function.depend_on_model(ResourceType)
    
    @aux_call
    @json_response({'resourceassignment__resource__name': 'room_name'})
    @needs_admin
    @cached_module_view
    def schedule_assignments(prog):
        data = ClassSection.objects.filter(status__gte=0, parent_class__status__gte=0, parent_class__parent_program=prog).select_related('resourceassignment__resource__name', 'resourceassignment__resource__event').extra({'timeslots': 'SELECT string_agg(to_char(resources_resource.event_id, \'999\'), \',\') FROM resources_resource, resources_resourceassignment WHERE resources_resource.id = resources_resourceassignment.resource_id AND resources_resourceassignment.target_id = program_classsection.id'}).values('id', 'resourceassignment__resource__name', 'timeslots').distinct()
        #   Convert comma-separated timeslot IDs to lists
        for i in range(len(data)):
            if data[i]['timeslots']:
                data[i]['timeslots'] = [int(x) for x in data[i]['timeslots'].strip().split(',')]
            else:
                data[i]['timeslots'] = []
        return {'schedule_assignments': list(data)}
    schedule_assignments.method.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    schedule_assignments.method.cached_function.depend_on_row(ResourceAssignment, lambda ra: {'prog': ra.target.parent_class.parent_program})
    
    @aux_call
    @json_response()
    @cached_module_view
    def timeslots(prog):
        timeslots = list(prog.getTimeSlots().extra({'label': """to_char("start", 'Dy HH:MI -- ') || to_char("end", 'HH:MI AM')"""}).values('id', 'short_description', 'label', 'start', 'end'))
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
    @json_response()
    @cached_module_view
    def lunch_timeslots(prog):
        lunch_timeslots = list(Event.objects.filter(meeting_times__parent_class__category__category="Lunch", meeting_times__parent_class__parent_program=prog).values('id'))
        for i in range(len(lunch_timeslots)):
            lunch_timeslots[i]['is_lunch'] = True
        return {'timeslots': lunch_timeslots}

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
        teacher_dict = {}
        teachers = []
        sections = list(prog.sections().values(
                'id',
                'status',
                'parent_class__anchor__friendly_name',
                'parent_class__id',
                'parent_class__category__symbol',
                'parent_class__anchor__name',
                'parent_class__grade_max',
                'parent_class__grade_min',
                'enrolled_students'))
        for section in sections:
            s = ClassSection.objects.get(id=section['id'])
            section['index'] = s.index()
            section['parent_class__anchor__name'] += "s" + str(section['index'])
            section['length'] = float(s.duration)
            section['teachers'] = [t.id for t in s.parent_class.teachers()]
            for t in s.parent_class.teachers():
                if teacher_dict.has_key(t.id):
                    continue
                teacher_dict[t.id] = True
                # Build up teacher availability
                availabilities = UserAvailability.objects.filter(user__in=s.parent_class.teachers()).filter(QTree(event__anchor__below = prog.anchor)).values('user_id', 'event_id')
                avail_for_user = defaultdict(list)
                for avail in availabilities:
                    avail_for_user[avail['user_id']].append(avail['event_id'])
                teachers.append({'id': t.id, 'first_name': t.first_name, 'last\
_name': t.last_name, 'availability': avail_for_user[t.id], 'sections': [x.id for x in t.getTaughtSectionsFromProgram(prog)]})
    
        return {'sections': sections, 'teachers': teachers}
    sections.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    sections.cached_function.depend_on_model(UserAvailability)
    # Put this import here rather than at the toplevel, because wildcard messes things up
    from esp.cache.key_set import wildcard
    sections.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'prog': self.parent_program})
    sections.cached_function.depend_on_cache(ClassSubject.teachers, lambda self=wildcard, **kwargs: {'prog': self.parent_program})

    @aux_call
    @json_response({
            'anchor__friendly_name': 'title',
            'category__symbol': 'category',
            'anchor__name': 'emailcode',
            })
    @cached_module_view
    def class_subjects(prog):
        teacher_dict = {}
        teachers = []
        classes = list(prog.classes().values(
                'id',
                'status',
                'anchor__friendly_name',
                'category__symbol',
                'anchor__name',
                'grade_max',
                'grade_min',
                'class_size_max',
                'message_for_directors',
                'requested_special_resources'))

        for cls in classes:
            c = ClassSubject.objects.get(id=cls['id'])
            cls['length'] = float(c.duration or 0.0)
            cls['sections'] = [s.id for s in c.sections.all()]
            cls['teachers'] = [t.id for t in c.teachers()]
            for t in c.teachers():
                if teacher_dict.has_key(t.id):
                    continue
                teacher_dict[t.id] = True
                # Build up teacher availability
                availabilities = UserAvailability.objects.filter(user__in=c.teachers()).filter(QTree(event__anchor__below = prog.anchor)).values('user_id', 'event_id')
                avail_for_user = defaultdict(list)
                for avail in availabilities:
                    avail_for_user[avail['user_id']].append(avail['event_id'])
                teachers.append({'id': t.id, 'first_name': t.first_name, 'last\
_name': t.last_name, 'availability': avail_for_user[t.id], 'sections': [x.id for x in t.getTaughtSectionsFromProgram(prog)]})
    
        return {'classes': classes, 'teachers': teachers}
    class_subjects.cached_function.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    # Put this import here rather than at the toplevel, because wildcard messes things up
    from esp.cache.key_set import wildcard
    class_subjects.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'prog': self.parent_program})
    class_subjects.cached_function.depend_on_cache(ClassSubject.teachers, lambda self=wildcard, **kwargs: {'prog': self.parent_program})

        
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
    @cached_module_view
    def class_info(self, request, tl, one, two, module, extra, prog):
        return_key = None
        if 'return_key' in request.GET:
            return_key = request.GET['return_key']
        if 'section_id' in request.GET:
            if return_key == None: return_key = 'sections'
            section_id = int(request.GET['section_id'])
            if return_key == 'sections':
                section = ClassSection.objects.get(pk=section_id)
            else:
                matching_classes = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            if return_key == None: return_key = 'classes'
            class_id = int(request.GET['class_id'])
            matching_classes = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError(False), 'Need a section or subject ID to fetch catalog info'

        # If we're here, we don't have a section_id, so default to classes
        if not return_key:
            return_key = 'classes'

        if return_key == 'sections':
            cls = section.parent_class
        else:
            cls = matching_classes[0]

        return_dict = {
            'id': cls.id if return_key == 'classes' else section_id,
            'status': cls.status,
            'emailcode': cls.emailcode(),
            'title': cls.title(),
            'class_info': cls.class_info, 
            'category': cls.category.category, 
            'difficulty': cls.hardness_rating,
            'prereqs': cls.prereqs, 
            'sections': [x.id for x in cls.sections.all()],
            'class_size_max': cls.class_size_max,
            'duration': cls.prettyDuration(),
            'grade_range': str(cls.grade_min) + "th to " + str(cls.grade_max) + "th grades" ,
        }

        return {return_key: [return_dict]}
    class_info.cached_function.depend_on_model(ClassSubject)
    class_info.cached_function.depend_on_model(ClassSection)

    @aux_call
    @cache_control(public=True, max_age=300)
    @json_response()
    def class_size_info(self, request, tl, one, two, module, extra, prog):
        return_key = None
        if 'return_key' in request.GET:
            return_key = request.GET['return_key']

        if 'section_id' in request.GET:
            if return_key == None: return_key = 'sections'
            section_id = int(request.GET['section_id'])
            if return_key == 'sections':
                section = ClassSection.objects.get(pk=section_id)
            else:
                target_qs = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            if return_key == None: return_key = 'classes'
            class_id = int(request.GET['class_id'])
            target_qs = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError(False), 'Need a section or subject ID to fetch catalog info'

        # If we're here, we don't have a section_id, so default to classes
        if not return_key:
            return_key = 'classes'

        if return_key == 'sections':
            cls = section.parent_class
        else:
            matching_classes = ClassSubject.objects.catalog_cached(prog, initial_queryset=target_qs)
            assert(len(matching_classes) == 1)
            cls = matching_classes[0]
        
        return_dict = {
            'id': cls.id if return_key == 'classes' else section_id,
            'class_size_min': cls.class_size_min,
            'class_size_max': cls.class_size_max,
            'optimal_class_size': cls.class_size_optimal,
            'optimal_class_size_ranges': cls.optimal_class_size_range.range_str() if cls.optimal_class_size_range else None,
            'allowable_class_size_ranges': [ cr.range_str() for cr in cls.get_allowable_class_size_ranges() ]            
        }

        if return_key == 'sections':
            return_dict['max_class_capacity'] = section.max_class_capacity
        
        return {return_key: [return_dict]}
            

    @aux_call
    @cache_control(public=True, max_age=300)
    @json_response()
    def class_admin_info(self, request, tl, one, two, module, extra, prog):
        return_key = None
        if 'return_key' in request.GET:
            return_key = request.GET['return_key']

        if 'section_id' in request.GET:
            if return_key == None: return_key = 'sections'
            section_id = int(request.GET['section_id'])
            if return_key == 'sections':
                section = ClassSection.objects.get(pk=section_id)
            else:
                target_qs = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            if return_key == None: return_key = 'classes'
            class_id = int(request.GET['class_id'])
            target_qs = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError(False), 'Need a section or subject ID to fetch catalog info'

        # If we're here, we don't have a section_id, so default to classes
        if not return_key:
            return_key = 'classes'

        if return_key == 'sections':
            cls = section.parent_class
        else:
            matching_classes = ClassSubject.objects.catalog_cached(prog, initial_queryset=target_qs)
            assert(len(matching_classes) == 1)
            cls = matching_classes[0]

        if return_key == 'sections':
            rrequests = ResourceRequest.objects.filter(target = section)
        else:
            rrequests = ResourceRequest.objects.filter(target__in = cls.sections.all())
        rrequest_dict = defaultdict(list)
        for r in rrequests:
            rrequest_dict[r.target_id].append((r.res_type_id, r.desired_value))

        cls = section.parent_class
        return_dict = {
            'id': cls.id if return_key == 'classes' else section_id,
            'resource_requests': rrequest_dict,
            'comments': cls.message_for_directors,
        }

        return {return_key: [return_dict]}
        
    @aux_call
    @json_response()
    @cached_module_view
    def message_requests():
        earlier_requests = MessageRequest.objects.exclude(subject__icontains='password recovery')
        data = earlier_requests.values('id', 'creator__first_name', 'creator__last_name', 'creator__username', 'subject', 'sender', 'processed_by', 'msgtext', 'recipients__useful_name').order_by('-id').distinct()
        for item in data:
            if isinstance(item['processed_by'], datetime):
                item['processed_by'] = item['processed_by'].timetuple()[:6]
        
        return {'message_requests': data}
    message_requests.cached_function.depend_on_model(lambda: MessageRequest)

    @aux_call
    @json_response()
    @cached_module_view
    def stats(prog):
        # Create a dictionary to assemble the output
        dictOut = { "stats": [] }

        classes = prog.classes().select_related()
        vitals = {'id': 'vitals'}

        class_num_list = []
        class_num_list.append(("Total # of Classes", len(classes)))
        class_num_list.append(("Total # of Class Sections", len(prog.sections().select_related())))
        class_num_list.append(("Total # of Lunch Classes", len(classes.filter(status=10))))
        class_num_list.append(("Total # of Classes <span style='color: #00C;'>Unreviewed</span>", len(classes.filter(status=0))))
        class_num_list.append(("Total # of Classes <span style='color: #0C0;'>Accepted</span>", len(classes.filter(status=10))))
        class_num_list.append(("Total # of Classes <span style='color: #C00;'>Rejected</span>", len(classes.filter(status=-10))))
        class_num_list.append(("Total # of Classes <span style='color: #990;'>Cancelled</span>", len(classes.filter(status=-20))))
        vitals['classnum'] = class_num_list

        proganchor = prog.anchor
        
        #   Display pretty labels for teacher and student numbers
        teacher_labels_dict = {}
        for module in prog.getModules():
            teacher_labels_dict.update(module.teacherDesc())
        vitals['teachernum'] = []

        ## Ew, queries in a for loop...
        ## Not much to be done about it, though;
        ## the loop is iterating over a list of independent queries and running each.
        teachers = prog.teachers()
        for key in teachers.keys():
            if key in teacher_labels_dict:
                vitals['teachernum'].append((teacher_labels_dict[key],         ## Unfortunately, 
len(teachers[key])))
            else:
                vitals['teachernum'].append((key, len(teachers[key])))
                
        student_labels_dict = {}
        for module in prog.getModules():
            student_labels_dict.update(module.studentDesc())      
        vitals['studentnum'] = []

        ## Ew, another set of queries in a for loop...
        ## Same justification, though.
        students = prog.students()
        for key in students.keys():
            if key in student_labels_dict:
                vitals['studentnum'].append((student_labels_dict[key], len(students[key])))
            else:
                vitals['studentnum'].append((key, len(students[key])))

        timeslots = prog.getTimeSlots()
        vitals['timeslots'] = []
        

        shours = 0.0
        chours = 0.0
        crhours = 0.0
        ## Write this as a 'for' loop because PostgreSQL can't do it in
        ## one go without a subquery or duplicated logic, and Django
        ## doesn't have enough power to expose either approach directly.
        ## At least there aren't any queries in the for loop...
        ## (In MySQL, this could I believe be done with a minimally-painful extra() clause.)
        ## Also, since we're iterating over a big data set, use .values()
        ## minimize the number of objects that we're creating.
        ## One dict and two Decimals per row, as opposed to
        ## an Object per field and all kinds of stuff...
        for cls in prog.classes().exclude(category__category='Lunch').annotate(num_sections=Count('sections'), subject_duration=Sum('sections__duration'), subject_students=Sum('sections__enrolled_students')).values('num_sections', 'subject_duration', 'subject_students', 'class_size_max'):
            if cls['subject_duration']:
                chours += float(cls['subject_duration'])
                shours += float(cls['subject_duration']) * (float(cls['class_size_max']) if cls['class_size_max'] else 0)
                crhours += float(cls['subject_duration']) * float(cls['subject_students']) / float(cls['num_sections'])
        vitals["hournum"] = []
        vitals["hournum"].append(("Total # of Class-Hours", chours))
        vitals["hournum"].append(("Total # of Class-Student-Hours (capacity)", shours))
        vitals["hournum"].append(("Total # of Class-Student-Hours (registered)", crhours))


        ## Prefetch enough data that get_meeting_times() and num_students() don't have to hit the db
        curclasses = ClassSection.prefetch_catalog_data(
            ClassSection.objects.filter(parent_class__parent_program = prog))

        ## Is it really faster to do this logic in Python?
        ## It'd be even faster to just write a raw SQL query to do it.
        ## But this is probably good enough.
        timeslot_dict = defaultdict(list)
        timeslot_set = set(timeslots)
        for section in curclasses:
            for timeslot in set.intersection(timeslot_set, section.get_meeting_times()):
                timeslot_dict[timeslot].append(section)

        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.short_description}
            
            curTimeslot['classcount'] = len(timeslot_dict[timeslot])

            def student_count(clslist):
                lst = [0] + [x.num_students() for x in clslist if x.category.category != 'Lunch']
                return reduce(operator.add, lst)

            def student_max_count(clslist):
                lst = [0] + [x.capacity for x in clslist if x.category.category != 'Lunch']
                return reduce(operator.add, lst)

            curTimeslot['studentcount'] = {
                'count': student_count(timeslot_dict[timeslot]),
                'max_count': student_max_count(timeslot_dict[timeslot])
                }
            
            vitals['timeslots'].append(curTimeslot)

        dictOut["stats"].append(vitals)

        shirt_data = {"id": "shirtnum"};
        adminvitals_shirt = prog.getShirtInfo()
        shirt_data["sizes"] = adminvitals_shirt['shirt_sizes'];
        shirt_data["types"] = adminvitals_shirt['shirt_types'];
        shirt_data["data"] = adminvitals_shirt['shirts'];
        dictOut["stats"].append(shirt_data);

        Q_categories = Q(program=prog)
        crmi = prog.getModuleExtension('ClassRegModuleInfo')
        if crmi.open_class_registration:
            Q_categories |= Q(pk=open_class_category().pk)
        #   Introduce a separate query to get valid categories, since the single query seemed to introduce duplicates
        program_categories = ClassCategories.objects.filter(Q_categories).distinct().values_list('id', flat=True)
        annotated_categories = ClassCategories.objects.filter(cls__parent_program=prog, cls__status__gte=0).annotate(num_subjects=Count('cls', distinct=True), num_sections=Count('cls__sections')).order_by('-num_subjects').values('id', 'num_sections', 'num_subjects', 'category').distinct()
        dictOut["stats"].append({"id": "categories", "data": filter(lambda x: x['id'] in program_categories, annotated_categories)})

        #   Add SplashInfo statistics if our program has them
        splashinfo_data = {}
        splashinfo_modules = filter(lambda x: isinstance(x, SplashInfoModule), prog.getModules('learn'))
        if len(splashinfo_modules) > 0:
            splashinfo_module = splashinfo_modules[0]
            tag_data = Tag.getProgramTag('splashinfo_choices', prog)
            if tag_data:
                splashinfo_choices = json.loads(tag_data)
            else:
                splashinfo_choices = {'lunchsat': SplashInfoForm.default_choices, 'lunchsun': SplashInfoForm.default_choices}
            for key in splashinfo_choices:
                counts = {}
                for item in splashinfo_choices[key]:
                    filter_kwargs = {'program': prog}
                    filter_kwargs[key] = item[0]
                    counts[item[1]] = SplashInfo.objects.filter(**filter_kwargs).distinct().count()
                splashinfo_data[key] = counts
            splashinfo_data['siblings'] = {
                'yes': SplashInfo.objects.filter(program=prog, siblingdiscount=True).distinct().count(),
                'no':  SplashInfo.objects.filter(program=prog).exclude(siblingdiscount=True).distinct().count()
            }
            dictOut["stats"].append({"id": "splashinfo", "data": splashinfo_data})
        
        return dictOut
    stats.cached_function.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    stats.cached_function.depend_on_row(SplashInfo, lambda si: {'prog': si.program})
    stats.cached_function.depend_on_row(Program, lambda prog: {'prog': prog})

    class Meta:
        abstract = True

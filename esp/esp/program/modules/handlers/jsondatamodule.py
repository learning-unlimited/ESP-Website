
from __future__ import absolute_import
from __future__ import division
from six.moves import range
from six.moves import zip
from functools import reduce
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
  Email: web-team@learningu.org
"""

from collections import defaultdict
from datetime import datetime
import operator

from django.views.decorators.cache import cache_control
from django.db.models import Count, Sum
from django.db.models.query import Q
from django.http import Http404

from argcache import cache_function

from esp.cal.models import Event
from esp.dbmail.models import MessageRequest
from esp.middleware import ESPError
from esp.program.class_status import ClassStatus
from esp.program.models import Program, ClassSection, ClassSubject, StudentRegistration, ClassCategories, StudentSubjectInterest, ClassFlagType, ClassFlag, ModeratorRecord, RegistrationProfile, TeacherBio, PhaseZeroRecord, FinancialAidRequest, VolunteerOffer
from esp.program.modules.base import ProgramModuleObj, CoreModule, needs_student_in_grade, needs_admin, no_auth, aux_call
from esp.resources.models import ResourceAssignment, ResourceRequest, ResourceType
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, UserAvailability, StudentInfo, Record
from esp.utils.decorators import cached_module_view, json_response
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.accounting.models import Transfer

from decimal import Decimal

class JSONDataModule(ProgramModuleObj, CoreModule):
    doc = """A program module dedicated to returning program-specific data in JSON form."""

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "JSON Data Module",
            "link_title": "JSON Data",
            "module_type": "json",
            "seq": 0,
            "choosable": 1,
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
                'id': classrooms_grouped[room_id][0].identical_id(prog),
                'uid': classrooms_grouped[room_id][0].identical_id(prog),
                'text': classrooms_grouped[room_id][0].name,
                'availability': [ r.event_id for r in classrooms_grouped[room_id] ],
                'associated_resources': [
                    {
                        'res_type_id': ar.res_type_id,
                        'value': ar.attribute_value,
                    }
                    for ar in classrooms_grouped[room_id][0].associated_resources()
                ],
                'num_students': classrooms_grouped[room_id][0].num_students,
            } for room_id in classrooms_grouped.keys() ]

        return {'rooms': classrooms_dicts}
    rooms.method.cached_function.depend_on_model('resources.Resource')

    @aux_call
    @json_response()
    @needs_admin
    @cached_module_view
    def moderators(prog):
        # Get any teacher that has either offered to moderate or is assigned as a moderator
        moderators = ESPUser.objects.filter(Q(moderatorrecord__program=prog, moderatorrecord__will_moderate=True) | Q(moderating_sections__parent_class__parent_program=prog))
        moderator_list = []
        for m in moderators:
            rec = ModeratorRecord.objects.filter(program=prog, user = m)
            mod_dict = {
                'id': m.id,
                'username': m.username,
                'first_name': m.first_name,
                'last_name': m.last_name,
                'sections': [s.id for s in m.getModeratingSectionsFromProgram(prog)],
            }
            if rec.exists():
                mod_dict.update({
                    'will_moderate': rec[0].will_moderate if rec.exists() else False,
                    'num_slots': rec[0].num_slots if rec.exists() else 0,
                    'categories': [c.id for c in rec[0].class_categories.all()] if rec.exists else [],
                    'comments': rec[0].comments if rec.exists() else "",
                })
            else:
                mod_dict.update({
                    'will_moderate': False,
                    'num_slots': 0,
                    'categories': [],
                    'comments': "",
                })
            moderator_list.append(mod_dict)
        for m in moderator_list:
            m['availability'] = [event.id for event in ESPUser.objects.get(id=m['id']).getAvailableTimes(prog, ignore_classes=True, ignore_moderation=True)]
        return {'moderators': moderator_list}
    moderators.method.cached_function.depend_on_m2m(ClassSection, 'moderators', lambda sec, moderator: {'prog': sec.parent_class.parent_program})
    moderators.method.cached_function.depend_on_model(ModeratorRecord)
    moderators.method.cached_function.depend_on_model(UserAvailability)

    @aux_call
    @json_response()
    @no_auth
    @cached_module_view
    def categories(prog):
        categories = prog.class_categories.all()
        if prog.open_class_registration:
            categories = categories.union(ClassCategories.objects.filter(pk=prog.open_class_category.pk))
        if len(categories) == 0:
            categories = ClassCategories.objects.filter(program__isnull=True)

        categories_dicts = [
            {
                'id': cat.id,
                'name': cat.category,
                'symbol': cat.symbol,
            }
            for cat in categories ]

        return {'categories': categories_dicts}
    categories.cached_function.depend_on_m2m(Program, 'class_categories', lambda prog, cat: {'prog': prog})

    @aux_call
    @json_response()
    @no_auth
    @cached_module_view
    def resource_types(prog):
        res_types = prog.getResourceTypes(include_global=Tag.getBooleanTag('allow_global_restypes'))
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
                'attributes': rt.attributes_dumped.split("|"),
            }
            for rt in res_types ]

        return {'resource_types': res_types_dicts}
    resource_types.cached_function.depend_on_model(ResourceType)

    @aux_call
    @json_response()
    @needs_admin
    @cached_module_view
    def schedule_assignments(prog):
        sections = prog.sections().prefetch_related('meeting_times')
        data_list = []
        for section in sections:
            room = None
            rooms = section.initial_rooms()
            if rooms.count() > 0:
                room = rooms[0]
            data_list.append({
                              'id': section.id,
                              'room_id': room.identical_id(prog) if room else None,
                              'room_name': room.name if room else None,
                              'timeslots': [time.id for time in section.get_meeting_times()]
                              })
        return {'schedule_assignments': data_list}
    schedule_assignments.method.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    schedule_assignments.method.cached_function.depend_on_row(ResourceAssignment, lambda ra: {'prog': ra.target.parent_class.parent_program})

    @aux_call
    @json_response()
    @no_auth
    @cached_module_view
    def timeslots(prog):
        timeslots = list(prog.getTimeSlots().extra({'label': """to_char("start", 'Dy MM/DD HH:MI -- ') || to_char("end", 'HH:MI AM')"""}).values('id', 'short_description', 'label', 'start', 'end'))
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
    @no_auth
    @cached_module_view
    def lunch_timeslots(prog):
        lunch_timeslots = list(Event.objects.filter(meeting_times__parent_class__category__category="Lunch", meeting_times__parent_class__parent_program=prog).values('id'))
        for i in range(len(lunch_timeslots)):
            lunch_timeslots[i]['is_lunch'] = True
        return {'timeslots': lunch_timeslots}
    lunch_timeslots.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})

    @aux_call
    @json_response()
    @no_auth
    @cached_module_view
    def sections(extra, prog):
        if extra == 'catalog':
            catalog = True
        elif extra is None:
            catalog = False
        else:
            raise Http404
        teacher_dict = {}
        teachers = []
        sections = []
        qs = prog.sections().prefetch_related(
            'parent_class__category',
            'parent_class__sections',
            'parent_class__teachers',
            'parent_class__parent_program',
            'meeting_times')

        for s in qs:
            section = {
                'id': s.id,
                'status': s.status,
                'parent_class': s.parent_class.id,
                'category': s.parent_class.category.symbol,
                'category_id': s.parent_class.category.id,
                'grade_max': s.parent_class.grade_max,
                'grade_min': s.parent_class.grade_min,
                'title': s.parent_class.title,
                'class_size_max': s.parent_class.class_size_max,
                'num_students': s.enrolled_students
            }
            sections.append(section)
            section['index'] = s.index()
            section['emailcode'] = s.emailcode()
            section['length'] = float(s.duration)
            if catalog:
                section['times'] = s.friendly_times_with_date()
                section['capacity'] = s.capacity
            section['moderators'] = [m.id for m in s.get_moderators()]
            class_teachers = s.parent_class.get_teachers()
            section['teachers'] = [t.id for t in class_teachers]
            for t in class_teachers:
                if t.id in teacher_dict:
                    teacher_dict[t.id]['sections'].append(s.id)
                    continue
                teacher = {
                    'id': t.id,
                    'username': t.username,
                    'first_name': t.first_name,
                    'last_name': t.last_name,
                    'sections': [s.id]
                }
                teachers.append(teacher)
                teacher_dict[t.id] = teacher

        # Build up teacher availability
        for teacher in teachers:
            teacher['availability'] = [event.id for event in ESPUser.objects.get(id=teacher['id']).getAvailableTimes(prog, ignore_classes=True)]

        return {'sections': sections, 'teachers': teachers}
    sections.cached_function.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    sections.cached_function.depend_on_m2m(ClassSection, 'moderators', lambda sec, moderator: {'prog': sec.parent_class.parent_program})
    sections.cached_function.depend_on_row(ClassSubject, lambda subj: {'prog': subj.parent_program})
    sections.cached_function.depend_on_model(UserAvailability)
    # Put this import here rather than at the toplevel, because wildcard messes things up
    from argcache.key_set import wildcard
    sections.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda self=wildcard, **kwargs: {'prog': self.parent_program})
    sections.cached_function.depend_on_cache(ClassSection.friendly_times, lambda self=wildcard, **kwargs: {'prog': self.parent_class.parent_program, 'extra': 'catalog'})
    sections.cached_function.depend_on_cache(ClassSection._get_capacity, lambda self=wildcard, **kwargs: {'prog': self.parent_class.parent_program, 'extra': 'catalog'})

    @aux_call
    @json_response()
    @needs_admin
    @cached_module_view
    def sections_admin(extra, prog):
        teacher_dict = {}
        teachers = []
        sections = []
        qs = prog.sections().prefetch_related(
            'parent_class__category',
            'parent_class__sections',
            'parent_class__teachers',
            'parent_class__parent_program',
            'meeting_times')

        for s in qs:
            rrequests = ResourceRequest.objects.filter(target = s)
            rrequest_dict = defaultdict(list)
            for r in rrequests:
                rrequest_dict[r.target_id].append((r.res_type_id, r.desired_value))

            cls = s.parent_class
            section = {
                'id': s.id,
                'status': s.status,
                'parent_class': cls.id,
                'category': cls.category.symbol,
                'category_id': cls.category.id,
                'class_style': cls.class_style,
                'grade_max': cls.grade_max,
                'grade_min': cls.grade_min,
                'title': cls.title,
                'class_size_max': cls.class_size_max,
                'num_students': s.enrolled_students,
                'resource_requests': rrequest_dict,
                'requested_room': cls.requested_room,
                'comments': cls.message_for_directors,
                'special_requests': cls.requested_special_resources,
                'flags': ', '.join(cls.flags.values_list('flag_type__name', flat=True)),
            }
            sections.append(section)
            section['index'] = s.index()
            section['emailcode'] = s.emailcode()
            section['length'] = float(s.duration)
            section['moderators'] = [m.id for m in s.get_moderators()]
            class_teachers = cls.get_teachers()
            section['teachers'] = [t.id for t in class_teachers]
            for t in class_teachers:
                if t.id in teacher_dict:
                    teacher_dict[t.id]['sections'].append(s.id)
                    continue
                teacher = {
                    'id': t.id,
                    'username': t.username,
                    'first_name': t.first_name,
                    'last_name': t.last_name,
                    'sections': [s.id],
                    'is_admin': t.isAdmin()
                }
                teachers.append(teacher)
                teacher_dict[t.id] = teacher

        # Build up teacher availability
        for teacher in teachers:
            teacher['availability'] = [event.id for event in ESPUser.objects.get(id=teacher['id']).getAvailableTimes(prog, ignore_classes=True)]

        return {'sections': sections, 'teachers': teachers}
    sections_admin.method.cached_function.depend_on_cache(sections.cached_function, lambda extra=wildcard, prog=wildcard, **kwargs: {'prog': prog, 'extra': extra})
    sections_admin.method.cached_function.depend_on_model(ResourceRequest)
    sections_admin.method.cached_function.depend_on_model(ClassFlag)

    @aux_call
    @json_response({
            'subject': 'id',
            'subject__sections': 'id',
            })
    @no_auth
    @cached_module_view
    def classes_timeslot(extra, prog):
        # TODO: make the /timeslots view do what we want and kill this one
        try:
            timeslot_id = int(extra)
        except (TypeError, ValueError):
            raise Http404

        section_ids = []
        subject_ids = []

        # Filter for any classes that overlap this timeslot first
        subjects = ClassSubject.objects.filter(
            parent_program=prog, sections__meeting_times__id__exact=timeslot_id)
        # Now select only classes that start at the given slot
        for cls in subjects:
            added = False
            for sec in cls.get_sections():
                meeting_times = sec.meeting_times.order_by('start')
                if (meeting_times.count() > 0 and
                    meeting_times[0].id == timeslot_id):
                    section_ids.append({'id': sec.id})
                    added = True
            if added:
                subject_ids.append({'id': cls.id})

        return {'timeslot_sections': section_ids,
                'timeslot_subjects': subject_ids}
    classes_timeslot.cached_function.depend_on_model(Event)
    classes_timeslot.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program, 'extra': str(event.id)})


    @aux_call
    @json_response()
    @no_auth
    @cached_module_view
    def class_subjects(extra, prog):
        if extra == 'catalog':
            catalog = True
        elif extra is None:
            catalog = False
        else:
            raise Http404
        teacher_dict = {}
        teachers = []
        classes = []
        qs = prog.classes().prefetch_related(
            'category', 'sections', 'teachers')

        for c in qs:
            class_teachers = c.get_teachers()
            cls = {
                'id': c.id,
                'status': c.status,
                'title': c.title,
                'category': c.category.symbol,
                'category_id': c.category.id,
                'grade_max': c.grade_max,
                'grade_min': c.grade_min,
            }
            classes.append(cls)
            if catalog:
                cls['class_info'] = c.class_info
                cls['class_style'] = c.class_style
                cls['difficulty'] = c.hardness_rating
                cls['prereqs'] = c.prereqs
            cls['emailcode'] = c.emailcode()
            if c.duration:
                cls['length'] = float(c.duration)
            cls['sections'] = [s.id for s in c.sections.all()]
            cls['teachers'] = [t.id for t in class_teachers]
            for t in class_teachers:
                if t.id in teacher_dict:
                    teacher_dict[t.id]['sections'] += cls['sections']
                    continue
                teacher = {
                    'id': t.id,
                    'username': t.username,
                    'first_name': t.first_name,
                    'last_name': t.last_name,
                    'sections': list(cls['sections'])
                }
                teachers.append(teacher)
                teacher_dict[t.id] = teacher

        # Build up teacher availability
        for teacher in teachers:
            teacher['availability'] = [event.id for event in ESPUser.objects.get(id=teacher['id']).getAvailableTimes(prog, ignore_classes=True)]

        return {'classes': classes, 'teachers': teachers}
    class_subjects.cached_function.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    class_subjects.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda cls=wildcard, **kwargs: {'prog': cls.parent_program})

    @aux_call
    @json_response({
            'subject': 'id',
            'subject__sections': 'id',
            })
    @needs_student_in_grade
    def interested_classes(self, request, tl, one, two, module, extra, prog):
        ssis = StudentSubjectInterest.valid_objects().filter(
            user=request.user)
        subject_ids = ssis.values('subject')
        section_ids = ssis.values('subject__sections')
        return {'interested_subjects': subject_ids,
                'interested_sections': section_ids}


    @aux_call
    @json_response()
    @needs_student_in_grade
    def lottery_preferences(self, request, tl, one, two, module, extra, prog):
        if prog.priorityLimit() > 1:
            return self.lottery_preferences_usepriority(request, prog)
        else:
            # TODO: determine if anything still relies on the legacy format.
            # merge the legacy format with the current format, just in case
            sections = self.lottery_preferences_usepriority(request, prog)['sections']
            sections_legacy = self.lottery_preferences_legacy(request, prog)['sections']
            sections_merged = []
            for item, item_legacy in zip(sections, sections_legacy):
                assert item['id'] == item_legacy['id']
                item_merged = dict(list(item_legacy.items()) + list(item.items()))
                sections_merged.append(item_merged)
            return {'sections': sections_merged}

    def lottery_preferences_legacy(self, request, prog):
        # DEPRECATED: see comments in lottery_preferences method
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

    def lottery_preferences_usepriority(self, request, prog):
        sections = list(prog.sections().values('id'))
        for i in range(1, prog.priorityLimit()+1, 1):
            priority_name = 'Priority/' + str(i)
            sections_priority = StudentRegistration.valid_objects().filter(relationship__name=priority_name, user=request.user, section__parent_class__parent_program=prog).select_related('section__id').values_list('section__id', flat=True).distinct()
            for item in sections:
                if item['id'] in sections_priority:
                    item[priority_name] = True
                #else:
                #   item['lottery_priority'] = False
        return {'sections': sections}


    @aux_call
    @cache_control(public=True, max_age=300)
    @json_response()
    @no_auth
    @cached_module_view
    def class_info(self, request, tl, one, two, module, extra, prog):
        return_key = None
        if 'return_key' in request.GET:
            return_key = request.GET['return_key']
        if 'section_id' in request.GET:
            if return_key is None: return_key = 'sections'
            section_id = int(request.GET['section_id'])
            if return_key == 'sections':
                section = ClassSection.objects.get(pk=section_id)
            else:
                matching_classes = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            if return_key is None: return_key = 'classes'
            class_id = int(request.GET['class_id'])
            matching_classes = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError('Need a section or subject ID to fetch catalog info', log=False)

        # If we're here, we don't have a section_id, so default to classes
        if not return_key:
            return_key = 'classes'

        if return_key == 'sections':
            cls = section.parent_class
        else:
            cls = matching_classes[0]

        section_info = []
        for sec in cls.get_sections():
            section_info.append({
                'num_students_priority': sec.num_students(['Priority/1']),
                'num_students_interested': sec.num_students(['Interested']),
                'num_students_enrolled': sec.num_students(['Enrolled']),
                'time': ', '.join(sec.friendly_times()),
                'room': ' and '.join(sec.prettyrooms()),
            })

        return_dict = {
            'id': cls.id if return_key == 'classes' else section_id,
            'status': cls.status,
            'emailcode': cls.emailcode(),
            'title': cls.title,
            'class_info': cls.class_info,
            'category': cls.category.category,
            'difficulty': cls.hardness_rating,
            'prereqs': cls.prereqs,
            'sections': section_info,
            'class_size_max': cls.class_size_max,
            'duration': cls.prettyDuration(),
            'location': ", ".join(cls.prettyrooms()),
            'grade_range': str(cls.grade_min) + "th to " + str(cls.grade_max) + "th grades",
        }

        return {return_key: [return_dict]}
    class_info.cached_function.depend_on_model(ClassSubject)
    class_info.cached_function.depend_on_model(ClassSection)

    @aux_call
    @cache_control(public=True, max_age=300)
    @json_response()
    @no_auth
    def class_size_info(self, request, tl, one, two, module, extra, prog):
        return_key = None
        if 'return_key' in request.GET:
            return_key = request.GET['return_key']

        if 'section_id' in request.GET:
            if return_key is None: return_key = 'sections'
            section_id = int(request.GET['section_id'])
            if return_key == 'sections':
                section = ClassSection.objects.get(pk=section_id)
            else:
                target_qs = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            if return_key is None: return_key = 'classes'
            class_id = int(request.GET['class_id'])
            target_qs = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError('Need a section or subject ID to fetch catalog info', log=False)

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

    # This is separate from class_info because students shouldn't see it
    @aux_call
    @cache_control(public=True, max_age=30)
    @json_response()
    @needs_admin
    def class_admin_info(self, request, tl, one, two, module, extra, prog):
        return_key = None
        if 'return_key' in request.GET:
            return_key = request.GET['return_key']

        if 'section_id' in request.GET:
            if return_key is None: return_key = 'sections'
            section_id = int(request.GET['section_id'])
            if return_key == 'sections':
                section = ClassSection.objects.get(pk=section_id)
            else:
                matching_classes = ClassSubject.objects.filter(sections=section_id)
        elif 'class_id' in request.GET:
            if return_key is None: return_key = 'classes'
            class_id = int(request.GET['class_id'])
            matching_classes = ClassSubject.objects.filter(id=class_id)
        else:
            raise ESPError('Need a section or subject ID to fetch catalog info', log=False)

        # If we're here, we don't have a section_id, so default to classes
        if not return_key:
            return_key = 'classes'

        if return_key == 'sections':
            cls = section.parent_class
        else:
            assert(len(matching_classes) == 1)
            cls = matching_classes[0]

        if return_key == 'sections':
            rrequests = ResourceRequest.objects.filter(target = section)
        else:
            rrequests = ResourceRequest.objects.filter(target__in = cls.sections.all())
        rrequest_dict = defaultdict(list)
        for r in rrequests:
            rrequest_dict[r.target_id].append((r.res_type_id, r.desired_value))

        section_info = []
        for sec in cls.get_sections():
            section_info.append({
                'num_students_priority': sec.num_students(['Priority/1']),
                'num_students_interested': sec.num_students(['Interested']),
                'num_students_enrolled': sec.num_students(['Enrolled']),
                'time': ', '.join(sec.friendly_times()),
                'room': ' and '.join(sec.prettyrooms()),
            })

        return_dict = {
            'id': cls.id if return_key == 'classes' else section_id,
            'status': cls.status,
            'is_scheduled': cls.hasScheduledSections(),
            'emailcode': cls.emailcode(),
            'title': cls.title,
            'class_info': cls.class_info,
            'category': cls.category.category,
            'class_style': cls.class_style,
            'difficulty': cls.hardness_rating,
            'prereqs': cls.prereqs,
            'sections': section_info,
            'class_size_max': cls.class_size_max,
            'duration': cls.prettyDuration(),
            'location': ", ".join(cls.prettyrooms()),
            'grade_range': str(cls.grade_min) + "th to " + str(cls.grade_max) + "th grades",
            'teacher_names': cls.pretty_teachers(),
            'moderator_names': cls.pretty_moderators(),
            'moderator_title': Tag.getProgramTag("moderator_title", prog).capitalize() + "s",
            'resource_requests': rrequest_dict,
            'comments': cls.message_for_directors,
            'special_requests': cls.requested_special_resources,
            'purchases': cls.purchase_requests,
            'flags': ', '.join(cls.flags.values_list('flag_type__name', flat=True)),
        }

        return {return_key: [return_dict]}


    @aux_call
    @json_response()
    @needs_admin
    @cached_module_view
    def message_requests():
        earlier_requests = MessageRequest.objects.all()
        # Limit to 100 so the data doesn't get too big for memcached
        data = earlier_requests.values('id', 'creator__first_name', 'creator__last_name', 'creator__username', 'subject', 'sender', 'processed_by', 'msgtext', 'recipients__useful_name').order_by('-id').distinct()[:100]
        for item in data:
            if isinstance(item['processed_by'], datetime):
                item['processed_by'] = item['processed_by'].timetuple()[:6]

        return {'message_requests': list(data)}

    message_requests.method.cached_function.depend_on_model('dbmail.MessageRequest')

    @cache_function
    def class_nums(prog):
        classes = prog.classes().select_related()
        sections = prog.sections().select_related()
        class_num_list = []
        class_num_list.append(("Total # of Classes", classes.distinct().count()))
        class_num_list.append(("Total # of Classes Scheduled", classes.filter(sections__meeting_times__isnull=False).distinct().count()))
        class_num_list.append(("Total # of Class Sections", sections.distinct().count()))
        class_num_list.append(("Total # of Class Sections Scheduled", sections.filter(meeting_times__isnull=False).distinct().count()))
        class_num_list.append(("Total # of Lunch Classes", classes.filter(category__category = "Lunch").filter(status=ClassStatus.ACCEPTED).distinct().count()))
        class_num_list.append(("Total # of Classes <span style='color: #00C;'>Unreviewed</span>", classes.filter(status=ClassStatus.UNREVIEWED).exclude(category__category='Lunch').distinct().count()))
        class_num_list.append(("Total # of Classes <span style='color: #0C0;'>Accepted</span>", classes.filter(status=ClassStatus.ACCEPTED, sections__status=ClassStatus.ACCEPTED).exclude(category__category='Lunch').distinct().count()))
        class_num_list.append(("Total # of Classes <span style='color: #C00;'>Rejected</span>", classes.filter(status=ClassStatus.REJECTED).exclude(category__category='Lunch').distinct().count()))
        class_num_list.append(("Total # of Classes <span style='color: #990;'>Cancelled</span>", classes.filter(status=ClassStatus.CANCELLED).exclude(category__category='Lunch').distinct().count()))
        return class_num_list
    class_nums.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    class_nums.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    class_nums.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})
    class_nums = staticmethod(class_nums)

    @cache_function
    def flags_nums(prog):
        classes = prog.classes().select_related()
        flags_num_list = []
        for ft in ClassFlagType.get_flag_types(prog):
            flags_num_list.append(('Total # of Classes with the <i><span style="color: %s;">%s</span></i> flag' % (ft.color, ft.name), classes.filter(flags__flag_type=ft).distinct().count()))
        return flags_num_list
    flags_nums.depend_on_row(ClassFlag, lambda flag: {'prog': flag.subject.parent_program})
    flags_nums = staticmethod(flags_nums)

    @cache_function
    def mod_nums(prog):
        teachers = prog.teachers()
        moderator_list = []
        if 'will_moderate' in teachers:
            moderator_list.append(("Teachers who have offered to be a " + Tag.getProgramTag("moderator_title", prog).lower(), teachers['will_moderate'].count()))
        if 'assigned_moderator' in teachers:
            moderator_list.append((Tag.getProgramTag("moderator_title", prog).capitalize() + "s who have been assigned to sections", teachers['assigned_moderator'].count()))
        moderator_list.append(("Total number of time blocks offered by " + Tag.getProgramTag("moderator_title", prog).lower() + "s", ModeratorRecord.objects.filter(program=prog).aggregate(Sum('num_slots'))['num_slots__sum'] or 0))
        moderator_list.append(("Total number of time blocks assigned " + Tag.getProgramTag("moderator_title", prog).lower() + "s", ClassSection.objects.filter(parent_class__parent_program=prog, moderators__isnull=False).distinct().aggregate(Count('meeting_times'))['meeting_times__count']))
        moderator_list.append(("Total number of sections assigned " + Tag.getProgramTag("moderator_title", prog).lower() + "s", ClassSection.objects.filter(parent_class__parent_program=prog, moderators__isnull=False).distinct().count()))
        return moderator_list
    mod_nums.depend_on_row(ModeratorRecord, lambda mr: {'prog': mr.program})
    mod_nums.depend_on_m2m(ClassSection, 'moderators', lambda sec, moderator: {'prog': sec.parent_class.parent_program})
    mod_nums.depend_on_model(Tag)
    mod_nums = staticmethod(mod_nums)

    @cache_function
    def cat_nums(prog):
        Q_categories = Q(program=prog)
        crmi = prog.classregmoduleinfo
        if crmi.open_class_registration:
            Q_categories |= Q(pk=prog.open_class_category.pk)
        #   Introduce a separate query to get valid categories, since the single query seemed to introduce duplicates
        program_categories = ClassCategories.objects.filter(Q_categories).distinct().values_list('id', flat=True)
        annotated_categories = ClassCategories.objects.filter(cls__parent_program=prog, cls__status__gte=0).annotate(num_subjects=Count('cls', distinct=True), num_sections=Count('cls__sections'), num_class_hours=Sum('cls__sections__duration')).order_by('-num_subjects').values('id', 'num_sections', 'num_subjects', 'num_class_hours', 'category').distinct()
        #   Convert Decimal values to float for serialization
        for i in range(len(annotated_categories)):
            if annotated_categories[i]['num_class_hours'] is None:
                annotated_categories[i]['num_class_hours'] = 0
            annotated_categories[i]['num_class_hours'] = float(annotated_categories[i]['num_class_hours'])
        return [x for x in annotated_categories if x['id'] in program_categories]
    cat_nums.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    cat_nums.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    cat_nums = staticmethod(cat_nums)

    @cache_function
    def grade_nums(prog):
        students = prog.students()
        classes = prog.classes().select_related()
        grades = [i for i in range(prog.grade_min, prog.grade_max+1)]
        # We can't perfectly trust most_recent_profile, but it's good enough for stats
        students_grades = students['enrolled'].filter(registrationprofile__most_recent_profile=True)
        students_grades = students_grades.values_list('registrationprofile__student_info__graduation_year')
        students_grades = students_grades.annotate(Count('id', distinct=True))
        grades_dict = {result[0]: result[1] for result in students_grades}
        grades_results = []
        for g in grades:
            year = ESPUser.YOGFromGrade(g, ESPUser.program_schoolyear(prog))
            grade_classes = classes.filter(status__gte=0, grade_min__lte=g, grade_max__gte=g)
            grade_sections = prog.sections().filter(status__gte=0, parent_class__in=grade_classes)
            grades_results.append({'grade': g, 'num_subjects': grade_classes.count(),
                                   'num_sections': grade_sections.count(),
                                   'num_students': grades_dict[year] if year in grades_dict else 0})
        return grades_results
    grade_nums.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    grade_nums.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    grade_nums.depend_on_model(StudentInfo) # I can't think of a more efficient way to depend on graduation year with depend_on_row -WG
    grade_nums = staticmethod(grade_nums)

    @cache_function
    def teacher_nums(prog):
        teachers = prog.teachers()
        teachers_qobjects = prog.teachers(QObjects = True)
        list_labels = prog.teacherDesc()
        teacher_num_list = []

        ## Ew, queries in a for loop...
        ## Not much to be done about it, though;
        ## the loop is iterating over a list of independent queries and running each.
        for key in teachers.keys():
            # This is useful for AUL/comm panel, but doesn't need to be on program dashboard
            if key not in ['taught_before']:
                if key in list_labels:
                    teacher_num_list.append((list_labels[key], teachers[key].filter(is_active = True).distinct().count()))
                else:
                    teacher_num_list.append((key, teachers[key].filter(is_active = True).distinct().count()))
                # Hack to insert this combined count in a logical position
                if key == 'class_submitted':
                    teacher_num_list.append(("""Teachers who have submitted a class and have not taught for a previous program""", ESPUser.objects.filter(~teachers_qobjects['taught_before'] & teachers_qobjects['class_submitted'] & Q(is_active = True)).distinct().count()))
        return teacher_num_list
    teacher_nums.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    teacher_nums.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    teacher_nums.depend_on_m2m(ClassSubject, 'teachers', lambda cls, teacher: {'prog': cls.parent_program})
    teacher_nums.depend_on_row(ResourceRequest, lambda rr: {'prog': rr.target.parent_class.parent_program})
    teacher_nums.depend_on_row(UserAvailability, lambda ua: {'prog': ua.event.program})
    teacher_nums.depend_on_row(RegistrationProfile, lambda prof: {'prog': prof.program})
    teacher_nums.depend_on_row(ClassFlag, lambda flag: {'prog': flag.subject.parent_program})
    teacher_nums.depend_on_row(Record, lambda rec: {'prog': rec.program})
    teacher_nums.depend_on_row(TeacherBio, lambda bio: {'prog': bio.program})
    teacher_nums = staticmethod(teacher_nums)

    @cache_function
    def student_nums(prog):
        students = prog.students()
        students_qobjects = prog.students(QObjects = True)
        list_labels = prog.studentDesc()
        student_num_list = []

        ## Ew, another set of queries in a for loop...
        ## Same justification, though.
        for key in students.keys():
            # These lists are useful for AUL/comm panel, but don't need to be on program dashboard
            if key not in ['attended_past', 'enrolled_past']:
                if key in list_labels:
                    student_num_list.append((list_labels[key], students[key].filter(is_active = True).distinct().count()))
                else:
                    student_num_list.append((key, students[key].filter(is_active = True).distinct().count()))
                # Hack to insert this combined count into a logical position
                if key == 'enrolled':
                    student_num_list.append(("""Students who are enrolled and have not enrolled in the past""", ESPUser.objects.filter(~students_qobjects['enrolled_past'] & students_qobjects['enrolled'] & Q(is_active = True)).distinct().count()))
        return student_num_list
    student_nums.depend_on_row(StudentSubjectInterest, lambda ssi: {'prog': ssi.subject.parent_program})
    student_nums.depend_on_row(StudentRegistration, lambda sr: {'prog': sr.section.parent_class.parent_program})
    student_nums.depend_on_row(RegistrationProfile, lambda prof: {'prog': prof.program})
    student_nums.depend_on_row(Record, lambda rec: {'prog': rec.program})
    student_nums.depend_on_row(PhaseZeroRecord, lambda rec: {'prog': rec.program})
    student_nums.depend_on_row(Transfer, lambda trans: {'prog': trans.line_item.program})
    student_nums.depend_on_row(FinancialAidRequest, lambda far: {'prog': far.program})
    student_nums = staticmethod(student_nums)

    @cache_function
    def volunteer_nums(prog):
        volunteers = prog.volunteers()
        list_labels = prog.volunteerDesc()
        volunteer_num_list = []

        ## Ew, another set of queries in a for loop...
        ## Same justification, though.
        for key in volunteers.keys():
            if key in list_labels:
                volunteer_num_list.append((list_labels[key], volunteers[key].filter(is_active = True).distinct().count()))
            else:
                volunteer_num_list.append((key, volunteers[key].filter(is_active = True).distinct().count()))
        return volunteer_num_list
    volunteer_nums.depend_on_row(VolunteerOffer, lambda vo: {'prog': vo.request.program})
    volunteer_nums = staticmethod(volunteer_nums)

    @staticmethod
    def calc_hours(classes):
        hours = {"class-hours": 0, "class-student-hours": 0, "class-registered-hours": 0, "class-checked-in-hours": 0}
        for cls in classes:
            if cls['subject_duration']:
                hours["class-hours"] += float(cls['subject_duration'])
                hours["class-student-hours"] += float(cls['subject_duration']) * (float(cls['class_size_max']) if cls['class_size_max'] else 0)
                hours["class-registered-hours"] += float(cls['subject_duration']) * float(cls['subject_students']) / float(cls['num_sections'])
                hours["class-checked-in-hours"] += float(cls['subject_duration']) * float(cls['subject_checked_in_students']) / float(cls['num_sections'])
        return hours

    @staticmethod
    def calc_section_hours(sections):
        hours = {"class-hours": 0, "class-student-hours": 0, "class-registered-hours": 0}
        for sec in sections:
            if sec['duration']:
                hours["class-hours"] += float(sec['duration'])
                capacity = ClassSection.objects.get(id=sec['id']).capacity
                hours["class-student-hours"] += float(sec['duration']) * float(capacity)
                hours["class-registered-hours"] += float(sec['duration']) * float(sec['enrolled_students'])
        return hours

    @cache_function
    def hour_nums(prog):
        ## Write this as a 'for' loop because PostgreSQL can't do it in
        ## one go without a subquery or duplicated logic, and Django
        ## doesn't have enough power to expose either approach directly.
        ## At least there aren't any queries in the for loop...
        ## (In MySQL, this could I believe be done with a minimally-painful extra() clause.)
        ## Also, since we're iterating over a big data set, use .values()
        ## minimize the number of objects that we're creating.
        ## One dict and two Decimals per row, as opposed to
        ## an Object per field and all kinds of stuff...
        reg_classes = prog.classes().exclude(category__category='Lunch').annotate(num_sections=Count('sections'), subject_duration=Sum('sections__duration'), subject_students=Sum('sections__enrolled_students'))
        for cls in reg_classes:
            cls.subject_checked_in_students = sum([sec.count_ever_checked_in_students() for sec in cls.get_sections()])
        reg_hours = JSONDataModule.calc_hours([{'num_sections': cls.num_sections, 'subject_duration': cls.subject_duration, 'subject_students': cls.subject_students, 'subject_checked_in_students': cls.subject_checked_in_students, 'class_size_max': cls.class_size_max} for cls in reg_classes])
        app_classes = prog.classes().filter(status__gt=0, sections__status__gt=0).exclude(category__category='Lunch').annotate(num_sections=Count('sections'), subject_duration=Sum('sections__duration'), subject_students=Sum('sections__enrolled_students'))
        for cls in app_classes:
            cls.subject_checked_in_students = sum([sec.count_ever_checked_in_students() for sec in cls.get_sections()])
        app_hours = JSONDataModule.calc_hours([{'num_sections': cls.num_sections, 'subject_duration': cls.subject_duration, 'subject_students': cls.subject_students, 'subject_checked_in_students': cls.subject_checked_in_students, 'class_size_max': cls.class_size_max} for cls in app_classes])
        sched_sections = prog.sections().filter(status__gt=0, meeting_times__isnull=False).exclude(parent_class__category__category='Lunch').values('duration', 'enrolled_students', 'id')
        sched_hours = JSONDataModule.calc_section_hours(sched_sections)
        hour_num_list = []
        hour_num_list.append(("Total # of Class-Hours (registered)", round(reg_hours["class-hours"], 2)))
        hour_num_list.append(("Total # of Class-Hours (approved)", round(app_hours["class-hours"], 2)))
        hour_num_list.append(("Total # of Class-Hours (scheduled)", round(sched_hours["class-hours"], 2)))
        hour_num_list.append(("Total # of Class-Student-Hours (registered)", round(reg_hours["class-student-hours"], 2)))
        hour_num_list.append(("Total # of Class-Student-Hours (approved)", round(app_hours["class-student-hours"], 2)))
        hour_num_list.append(("Total # of Class-Student-Hours (scheduled)", round(sched_hours["class-student-hours"], 2)))
        hour_num_list.append(("Total # of Class-Student-Hours (enrolled)", round(reg_hours["class-registered-hours"], 2)))
        hour_num_list.append(("Total # of Class-Student-Hours (attended program)", round(reg_hours["class-checked-in-hours"], 2)))
        if sched_hours["class-student-hours"]:
            hour_num_list.append(("Class-Student-Hours Utilization", str(round(100 * reg_hours["class-registered-hours"] / sched_hours["class-student-hours"], 2)) + "%"))
        return hour_num_list
    hour_nums.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    hour_nums.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    hour_nums.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})
    hour_nums.depend_on_row(StudentRegistration, lambda sr: {'prog': sr.section.parent_class.parent_program})
    hour_nums.depend_on_row(Record, lambda rec: {'prog': rec.program}, lambda rec: rec.event and rec.event.name == 'attended')
    hour_nums = staticmethod(hour_nums)

    @cache_function
    def timeslots_nums(prog):
        ## Prefetch enough data that get_meeting_times() and num_students() don't have to hit the db
        curclasses = ClassSection.prefetch_catalog_data(
            ClassSection.objects
            .filter(parent_class__parent_program=prog)
            .select_related('parent_class', 'parent_class__category'))

        timeslots = prog.getTimeSlots()
        timeslots_num_list = []
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

            timeslots_num_list.append(curTimeslot)
        return timeslots_num_list
    timeslots_nums.depend_on_row(ClassSubject, lambda cls: {'prog': cls.parent_program})
    timeslots_nums.depend_on_row(ClassSection, lambda sec: {'prog': sec.parent_class.parent_program})
    timeslots_nums.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})
    timeslots_nums.depend_on_row(StudentRegistration, lambda sr: {'prog': sr.section.parent_class.parent_program})
    timeslots_nums = staticmethod(timeslots_nums)

    @aux_call
    @json_response()
    @needs_admin
    def stats(self, request, tl, one, two, module, extra, prog):
        # Create a dictionary to assemble the output
        dictOut = { "stats": [] }

        vitals = {'id': 'vitals'}
        vitals['classnum'] = self.class_nums(prog)
        vitals['flagsnum'] = self.flags_nums(prog)
        vitals['teachernum'] = self.teacher_nums(prog)
        vitals['studentnum'] = self.student_nums(prog)
        vitals['volunteernum'] = self.volunteer_nums(prog)

        if prog.hasModule("TeacherModeratorModule"):
            vitals['moderatornum'] = self.mod_nums(prog)

        vitals["hournum"] = self.hour_nums(prog)
        vitals['timeslots'] = self.timeslots_nums(prog)

        dictOut["stats"].append(vitals)

        shirt_data = {"id": "shirtnum"};
        shirt_data["moderator_title"] = Tag.getProgramTag("moderator_title", prog).capitalize();
        adminvitals_shirt = prog.getShirtInfo()
        shirt_data["types"] = adminvitals_shirt['shirt_types'];
        shirt_data["data"] = adminvitals_shirt['shirts'];
        dictOut["stats"].append(shirt_data);

        dictOut["stats"].append({"id": "categories", "data": self.cat_nums(prog)})

        ## Calculate the grade data:
        dictOut["stats"].append({"id": "grades", "data": self.grade_nums(prog)})

        #   Add accounting stats
        pac = ProgramAccountingController(prog)
        (num_payments, total_payment) = pac.payments_summary()
        accounting_data = {
            'num_payments': num_payments,
            # We need to convert to a float in order for json to serialize it.
            # Since we're not doing any computation client-side with these
            # numbers, this doesn't cause accuracy issues.  If the
            # total_payment is None, just coerce it to zero for display
            # purposes.
            'total_payments': float(total_payment or 0),
        }
        dictOut["stats"].append({"id": "accounting", "data": accounting_data})

        return dictOut

    @aux_call
    @needs_student_in_grade
    def set_donation_amount(self, request, tl, one, two, module, extra, prog):
        """ Set the student's desired donation amount.
            Creates a line item type for donations if it does not exist. """

        amount_donation = Decimal(request.POST.get('amount', '0'))
        iac = IndividualAccountingController(prog, request.user)
        #   Clear the Transfers by specifying quantity 0
        iac.set_preference('Donation to Learning Unlimited', 0)
        if amount_donation != Decimal('0'):
            #   Specify quantity 1 and the desired amount
            iac.set_preference('Donation to Learning Unlimited', 1, amount=amount_donation)

    @aux_call
    @json_response()
    @needs_admin
    def teachers_for_autoscheduler(self, request, tl, one, two, module, extra, prog):
        """Dump teachers in a JSON format to be fed into the autoscheduler.

        Unfortunately, the view name "teachers" conflicts with magic in the
        Program class, so we have to name it something else.

        Note that this code isn't normally accessed from the website interface.
        """

        teachers = ESPUser.objects.filter(classsubject__parent_program=prog).distinct()

        teacher_dicts = [
            {   'uid': t.id,
                'text': t.name(),
                'availability': [event.id for event in t.getAvailableTimes(prog, ignore_classes=True)]
            } for t in teachers ]

        return {'teachers': teacher_dicts}

    class Meta:
        proxy = True
        app_label = 'modules'

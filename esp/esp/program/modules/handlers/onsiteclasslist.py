
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

import json
from datetime import datetime, timedelta

from django.db.models import Min
from django.db.models.query import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe


from esp.users.models    import ESPUser, Record, ContactInfo, StudentInfo, K12School
from esp.program.models import RegistrationProfile

from esp.program.modules.base import ProgramModuleObj, needs_onsite, needs_student, main_call, aux_call
from esp.program.models import ClassSubject, ClassSection, StudentRegistration, ScheduleMap, Program
from esp.utils.web import render_to_response
from esp.cal.models import Event
from argcache import cache_function
from esp.users.models import ESPUser, Record
from esp.resources.models import ResourceAssignment
from esp.utils.models import Printer, PrintRequest
from esp.utils.query_utils import nest_Q
from esp.tagdict.models import Tag
from esp.accounting.controllers import IndividualAccountingController

class OnSiteClassList(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Show Open Classes at Onsite Registration",
            "link_title": "List of Open Classes",
            "module_type": "onsite",
            "seq": 32,
            "choosable": 1,
            }

    @cache_function
    def section_data(sec):
        sect = {}
        sect['id'] = sec.id
        sect['emailcode'] = sec.emailcode()
        sect['title'] = sec.title()
        sect['teachers'] = ', '.join([t.name() for t in list(sec.teachers)])
        sect['rooms'] = (' ,'.join(sec.prettyrooms()))[:12]
        return sect
    section_data.depend_on_model('resources.ResourceAssignment')
    section_data.depend_on_cache(ClassSubject.get_teachers, lambda **kwargs: {})
    section_data=staticmethod(section_data)

    """ Warning: for performance reasons, these views are not abstracted away from
        the models.  If the schema is changed this code will need to be updated.
    """

    @aux_call
    @needs_onsite
    def catalog_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        #   Fetch a reduced version of the catalog to save time
        sections = list(ClassSection.objects.filter(parent_class__parent_program=prog, status__gt=0).extra({'event_ids':  """ARRAY(SELECT "cal_event"."id" FROM "cal_event", "program_classsection_meeting_times" WHERE ("program_classsection_meeting_times"."event_id" = "cal_event"."id" AND "program_classsection_meeting_times"."classsection_id" = "program_classsection"."id"))"""}).values('id', 'parent_class__id', 'enrolled_students', 'event_ids', 'registration_status'))
        for i in range(0, len(sections)):
            sections[i]['capacity'] = ClassSection.objects.get(id=sections[i]['id']).capacity
        data = {
            #   Todo: section current capacity ? (see ClassSection.get_capacity())
            'classes': list(ClassSubject.objects.filter(parent_program=prog, status__gt=0).extra({'teacher_names': """array_to_string(ARRAY(SELECT auth_user.first_name || ' ' || auth_user.last_name FROM auth_user,program_class_teachers WHERE program_class_teachers.classsubject_id=program_class.id AND auth_user.id=program_class_teachers.espuser_id), ', ')""", 'class_size_max_optimal': """SELECT program_classsizerange.range_max FROM program_classsizerange WHERE program_classsizerange.id = optimal_class_size_range_id"""}).values('id', 'class_size_max', 'class_size_max_optimal', 'class_info', 'prereqs', 'hardness_rating', 'grade_min', 'grade_max', 'title', 'teacher_names', 'category__symbol', 'category__id')),
            'sections': sections,
            'timeslots': list(prog.getTimeSlots().extra({'start_millis':"""EXTRACT(EPOCH FROM start) * 1000""",'label': """to_char("start", 'Dy HH:MI -- ') || to_char("end", 'HH:MI AM')"""}).values_list('id', 'label','start_millis').order_by("start")),
            'categories': list(prog.class_categories.all().order_by('-symbol').values('id', 'symbol', 'category')),
        }
        json.dump(data, resp)

        return resp

    @aux_call
    @needs_onsite
    def enrollment_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        data = StudentRegistration.valid_objects().filter(section__status__gt=0, section__parent_class__status__gt=0, section__parent_class__parent_program=prog, relationship__name='Enrolled').values_list('user__id', 'section__id')
        json.dump(list(data), resp)
        return resp

    @aux_call
    @needs_onsite
    def students_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        #   Try to ensure we don't miss anyone

        students_dict = self.program.students(QObjects=True)
        search_query = request.GET.get('q')

        student_types = ['student_profile']     #   You could add more list names here, but it would get very slow.
        students_Q = Q()

        for student_type in student_types:
            students_Q = students_Q | students_dict[student_type]

        students = ESPUser.objects.filter(students_Q)
        program_students_ids = []

        if search_query:
            #If user provided a search term then we want to expand search to the
            #entire student base

            search_tokens = search_query.split(' ')
            search_qset = Q()

            for token in search_tokens:
                search_qset = search_qset & (Q(last_name__icontains=token) | Q(first_name__icontains=token))

            program_students_ids = set(students.values_list('id', flat=True).distinct())
            students = ESPUser.objects.filter(search_qset)

        students = students.values_list('id', 'last_name', 'first_name') \
                           .distinct() \
                           .order_by('first_name', 'last_name')

        data = []
        for student in students:
            has_profile = not search_query or student[0] in program_students_ids
            data.append(list(student) + [has_profile])

        data.sort(key=lambda x: not x[3])
        if search_query:
            data = data[:20]

        json.dump(data, resp)
        return resp

    @aux_call
    @needs_onsite
    def register_student(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        program = self.program
        success = False
        student = get_object_or_404(ESPUser,pk=request.POST.get("student_id"))

        registration_profile = RegistrationProfile.getLastForProgram(student,
                                                                program)
        success = registration_profile.student_info is not None

        if success:
            registration_profile.save()

            for extension in ['paid','Attended','medical','liability','OnSite']:
                Record.createBit(extension, program, student)

            IndividualAccountingController.updatePaid(self.program, student, paid=True)

        json.dump({'status':success}, resp)
        return resp

    @aux_call
    @needs_onsite
    def checkin_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        students = prog.students(True)
        data = ESPUser.objects.filter(students['attended'] & ~students['checked_out']).distinct().values_list('id')
        json.dump(list(data), resp)
        return resp

    @aux_call
    @needs_onsite
    def counts_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        data = ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog).values_list('id', 'enrolled_students', 'attending_students')
        json.dump(list(data), resp)
        return resp

    @aux_call
    @needs_onsite
    def full_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        data = [[section.id, section.isFull(webapp=True)] for section in
                     ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0,
                                                 parent_class__parent_program=prog)]
        json.dump(data, resp)
        return resp

    @aux_call
    @needs_onsite
    def rooms_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        data = ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, resourceassignment__resource__res_type__name="Classroom").select_related('resourceassignment__resource__name').values_list('id', 'resourceassignment__resource__name', 'resourceassignment__resource__num_students')
        json.dump(list(data), resp)
        return resp

    @aux_call
    @needs_onsite
    def get_schedule_json(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        result = {'user': None, 'user_grade': 0, 'sections': [], 'messages': []}
        try:
            result['user'] = int(request.GET['user'])
        except:
            result['messages'].append('Error: no user specified.')
        if result['user']:
            result['user_grade'] = ESPUser.objects.get(id=result['user']).getGrade(program=prog)
            result['sections'] = list(ClassSection.objects.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'), status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, studentregistration__relationship__name='Enrolled', studentregistration__user__id=result['user']).values_list('id', flat=True).distinct())
        json.dump(result, resp)
        return resp

    @aux_call
    @needs_onsite
    def update_schedule_json(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')
        result = {'user': None, 'sections': [], 'messages': []}
        try:
            user = ESPUser.objects.get(id=int(request.GET['user']))
        except:
            user = None
            result['messages'].append('Error: could find user %s' % request.GET.get('user', None))
        try:
            desired_sections = json.loads(request.GET['sections'])
        except:
            result['messages'].append('Error: could not parse requested sections %s' % request.GET.get('sections', None))
            desired_sections = None

        #   Check in student if not currently checked in, since if they're using this view they must be onsite
        if not prog.isCheckedIn(user):
            rec = Record(user=user, program=prog, event='attended')
            rec.save()

        if user and desired_sections is not None:
            override_full = (request.GET.get("override", "") == "true")

            current_sections = list(ClassSection.objects.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'), status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, studentregistration__relationship__name='Enrolled', studentregistration__user__id=user.id).values_list('id', flat=True).order_by('id').distinct())
            sections_to_remove = ClassSection.objects.filter(id__in=list(set(current_sections) - set(desired_sections)))
            sections_to_add = ClassSection.objects.filter(id__in=list(set(desired_sections) - set(current_sections)))

            failed_add_sections = []
            for sec in sections_to_add:
                if sec.isFull(webapp=True) and not override_full:
                    result['messages'].append('Failed to add %s (%s) to %s: %s (%s).  Error was: %s' % (user.name(), user.id, sec.emailcode(), sec.title(), sec.id, 'Class is currently full.'))
                    failed_add_sections.append(sec.id)

            if len(failed_add_sections) == 0:
                #   Remove sections the student wants out of
                for sec in sections_to_remove:
                    sec.unpreregister_student(user)
                    result['messages'].append('Removed %s (%s) from %s: %s (%s)' % (user.name(), user.id, sec.emailcode(), sec.title(), sec.id))

                #   Remove sections that conflict with those the student wants into
                sec_times = sections_to_add.select_related('meeting_times__id').values_list('id', 'meeting_times__id').order_by('meeting_times__id').distinct()
                sm = ScheduleMap(user, prog)
                existing_sections = []
                for (sec, ts) in sec_times:
                    if ts and ts in sm.map and len(sm.map[ts]) > 0:
                        #   We found something we need to remove
                        for sm_sec in sm.map[ts]:
                            if sm_sec.id not in sections_to_add:
                                sm_sec.unpreregister_student(user)
                                result['messages'].append('Removed %s (%s) from %s: %s (%s)' % (user.name(), user.id, sm_sec.emailcode(), sm_sec.title(), sm_sec.id))
                            else:
                                existing_sections.append(sm_sec)

                #   Add the sections the student wants
                for sec in sections_to_add:
                    if sec not in existing_sections and sec.id not in failed_add_sections:
                        error = sec.cannotAdd(user, not override_full, webapp=True)
                        if not error:
                            reg_result = sec.preregister_student(user, overridefull=override_full, webapp=True)
                            if not reg_result:
                                error = 'Class is currently full.'
                        else:
                            reg_result = False
                        if reg_result:
                            result['messages'].append('Added %s (%s) to %s: %s (%s)' % (user.name(), user.id, sec.emailcode(), sec.title(), sec.id))
                        else:
                            result['messages'].append('Failed to add %s (%s) to %s: %s (%s).  Error was: %s' % (user.name(), user.id, sec.emailcode(), sec.title(), sec.id, error))

            result['user'] = user.id
            result['sections'] = list(ClassSection.objects.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'), status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, studentregistration__relationship__name='Enrolled', studentregistration__user__id=result['user']).values_list('id', flat=True).distinct())

        json.dump(result, resp)
        return resp


    """ End of highly model-dependent JSON views    """

    @aux_call
    @needs_onsite
    def printschedule_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(content_type='application/json')

        result = {}

        try:
            user = int(request.GET.get('user', None))
            user_obj = ESPUser.objects.get(id=user)
        except:
            result['message'] = "Could not find user %s." % request.GET.get('user', None)

        printer = request.GET.get('printer',None)
        if printer is not None:
            # we could check that it exists and is unique first, but if not, that should be an error anyway, and it isn't the user's fault unless they're trying to mess with us, so a 500 is reasonable and gives us better debugging output.
            printer = Printer.objects.get(name=printer)
        req = PrintRequest.objects.create(user=user_obj, printer=printer)
        result['message'] = "Submitted %s's schedule for printing (print request #%s)." % (user_obj.name(), req.id)

        json.dump(result, resp)
        return resp

    @aux_call
    @needs_onsite
    def classchange_grid(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['timeslots'] = prog.getTimeSlots()
        context['printers'] = Printer.objects.all().values_list('name', flat=True)
        context['initial_student'] = request.GET.get('student_id', '')

        open_class_category = prog.open_class_category
        open_class_category = dict( [ (k, getattr( open_class_category, k )) for k in ['id','symbol','category'] ] )
        context['open_class_category'] = mark_safe(json.dumps(open_class_category))

        return render_to_response(self.baseDir()+'ajax_status.html', request, context)

    @aux_call
    @needs_onsite
    def classList(self, request, tl, one, two, module, extra, prog):
        return self.classList_base(request, tl, one, two, module, extra, prog, template_name='classlist.html')

    @aux_call
    @needs_student
    def classlist_public(self, request, tl, one, two, module, extra, prog):
        return self.classList_base(request, tl, one, two, module, extra, prog, options={}, template_name='allclass_fragment.html')

    def classList_base(self, request, tl, one, two, module, extra, prog, options=None, template_name='classlist.html'):
        """ Display a list of all classes that still have space in them """

        #   Allow options to be supplied as an argument to the view function, in lieu
        #   of request.GET (used by the public view just above)
        if options is None:
            options = request.GET.copy()

            #   Display options-selection page if this page is requested with no GET variables
            if len(options.keys()) == 0:
                return render_to_response(self.baseDir() + 'classlist_options.html', request, {'prog': prog})

        context = {}
        defaults = {'refresh': 120, 'scrollspeed': 1}
        for key_option in defaults.keys():
            if key_option in options:
                context[key_option] = options[key_option]
            else:
                context[key_option] = defaults[key_option]

        time_now = datetime.now()

        start_id = int(options.get('start', -1))
        if start_id != -1:
            curtime = Event.objects.filter(id=start_id)
        else:
            window_start = time_now + timedelta(-1, 85200)  # 20 minutes ago
            curtime = Event.objects.filter(start__gte=window_start, event_type__description='Class Time Block').order_by('start')

        end_id = int(options.get('end', -1))
        if end_id != -1:
            endtime = Event.objects.filter(id=end_id)
        else:
            endtime = None

        sort_spec = options.get('sorting', None)
        if sort_spec is None:
            sort_spec = extra

        #   Enforce a maximum refresh speed to avoid server overload.
        min_refresh = int(Tag.getTag('onsite_classlist_min_refresh'))
        if int(context['refresh']) < min_refresh:
            context['refresh'] = min_refresh

        if curtime:
            curtime = curtime[0]
            if endtime:
                endtime = endtime[0]
                classes = self.program.sections().annotate(begin_time=Min("meeting_times__start")).filter(
                    status=10, parent_class__status=10,
                    begin_time__gte=curtime.start, begin_time__lte=endtime.start
                    )
            else:
                 classes = self.program.sections().annotate(begin_time=Min("meeting_times__start")).filter(
                     status=10, parent_class__status=10,
                     begin_time__gte=curtime.start
                     )
            if sort_spec == 'unsorted':
                classes = classes.order_by('begin_time', 'id').distinct()
            elif sort_spec == 'by_time':
                classes = classes.order_by('begin_time', 'parent_class__category', 'id').distinct()
            else:
                classes = classes.order_by('parent_class__category', 'begin_time', 'id').distinct()

        context.update({'prog': prog, 'current_time': curtime, 'classes': classes, 'one': one, 'two': two})

        if sort_spec == 'unsorted':
            context['use_categories'] = False
        else:
            context['use_categories'] = True

        return render_to_response(self.baseDir()+template_name, request, context)

    @main_call
    @needs_onsite
    def allClassList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """

        #   This view still uses classes, not sections.  The templates show information
        #   for each section of each class.
        classes = [(i.num_students()/(i.class_size_max + 1), i) for i in self.program.classes()]
        classes.sort()
        classes = [i[1] for i in classes]

        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id': cls.category_id, 'category': cls.category.category}

        printers = [ x.name for x in Printer.objects.all() ]

        return render_to_response(self.baseDir()+'allclasslist.html', request,
            {'classes': classes, 'prog': self.program, 'one': one, 'two': two, 'categories': categories.values(), 'printers': printers})

    def makeLink(self):
        calls = [("classchange_grid","Grid-based Class Changes Interface"), ("classList","Scrolling Class List"), (self.get_main_view(),self.module.link_title)]
        strings = [u'<a href="%s" title="%s" class="vModuleLink" >%s</a>' % \
                ('/' + self.module.module_type + '/' + self.program.url + '/' + call[0], call[1], call[1]) for call in calls]
        return "</li><li>".join(strings)



    class Meta:
        proxy = True
        app_label = 'modules'


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

from datetime import datetime, timedelta
from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.program.models import ClassSubject, ClassSection, StudentRegistration, ScheduleMap
from esp.web.util import render_to_response
from esp.cal.models import Event
from esp.cache import cache_function
from esp.users.models import ESPUser, UserBit
from esp.resources.models import ResourceAssignment
from esp.datatree.models import *
from django.db.models import Min
from django.db.models.query import Q
from django.http import HttpResponse

import simplejson
import colorsys

def hsl_to_rgb(hue, saturation, lightness=0.5):
    (red, green, blue) = colorsys.hls_to_rgb(hue, lightness, saturation)
    return '%02x%02x%02x' % (min(1.0, red) * 255.0, min(1.0, green) * 255.0, min(1.0, blue) * 255.0)

class OnSiteClassList(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Show All Classes at Onsite Registration",
            "link_title": "List of All Classes",
            "module_type": "onsite",
            "seq": 31,
            }, {
            "admin_title": "Show Open Classes at Onsite Registration",
            "link_title": "List of Open Classes",
            "module_type": "onsite",
            "seq": 32,
            } ]

    @cache_function
    def section_data(sec):
        sect = {}
        sect['id'] = sec.id
        sect['emailcode'] = sec.emailcode()
        sect['title'] = sec.title()
        sect['teachers'] = ', '.join([t.name() for t in list(sec.teachers)])
        sect['rooms'] = (' ,'.join(sec.prettyrooms()))[:12]
        return sect
    section_data.depend_on_model(lambda: ResourceAssignment)
    section_data.depend_on_cache(lambda: ClassSubject.teachers, lambda **kwargs: {})
    section_data = staticmethod(section_data)


    """ Warning: for performance reasons, these views are not abstracted away from
        the models.  If the schema is changed this code will need to be updated.
    """
    
    @aux_call
    @needs_onsite
    def catalog_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        #   Fetch a reduced version of the catalog to save time
        data = {
            #   Todo: section current capacity ? (see ClassSection.get_capacity())
            'classes': list(ClassSubject.objects.filter(parent_program=prog, status__gt=0).extra({'teacher_names': """SELECT array_to_string(array_agg(auth_user.first_name || ' ' || auth_user.last_name), ', ') FROM users_userbit, auth_user, datatree_datatree WHERE users_userbit.user_id = auth_user.id AND	users_userbit.qsc_id = program_class.anchor_id 	AND	users_userbit.verb_id = datatree_datatree.id AND datatree_datatree.uri = 'V/Flags/Registration/Teacher'""", 'class_size_max_optimal': """SELECT	program_classsizerange.range_max FROM program_classsizerange WHERE program_classsizerange.id = optimal_class_size_range_id"""}).values('id', 'class_size_max', 'class_size_max_optimal', 'class_info', 'grade_min', 'grade_max', 'anchor__name', 'anchor__friendly_name', 'teacher_names', 'category__symbol')),
            'sections': list(ClassSection.objects.filter(parent_class__parent_program=prog, status__gt=0).extra({'event_ids':  """SELECT list("cal_event"."id") FROM "cal_event", "program_classsection_meeting_times" WHERE ("program_classsection_meeting_times"."event_id" = "cal_event"."id" AND "program_classsection_meeting_times"."classsection_id" = "program_classsection"."id")"""}).values('id', 'max_class_capacity', 'parent_class__id', 'anchor__name', 'enrolled_students', 'event_ids')),
            'timeslots': list(prog.getTimeSlots().extra({'label': """to_char("start", 'Dy HH:MI -- ') || to_char("end", 'HH:MI AM')"""}).values_list('id', 'label')),
            'categories': list(prog.class_categories.all().order_by('-symbol').values('id', 'symbol', 'category')),
        }
        simplejson.dump(data, resp)
        return resp
    
    @aux_call
    @needs_onsite
    def enrollment_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        data = StudentRegistration.objects.filter(section__status__gt=0, section__parent_class__status__gt=0, end_date__gte=datetime.now(), start_date__lte=datetime.now(), section__parent_class__parent_program=prog, relationship__name='Enrolled').values_list('user__id', 'section__id')
        simplejson.dump(list(data), resp)
        return resp
    
    @aux_call
    @needs_onsite
    def students_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        grade_query = """
SELECT (12 + %d - "users_studentinfo"."graduation_year")
FROM "users_studentinfo", "program_registrationprofile"
WHERE
    "program_registrationprofile"."most_recent_profile" = true
AND	"program_registrationprofile"."student_info_id" = "users_studentinfo"."id"
AND	"users_studentinfo"."user_id" = "auth_user"."id"
ORDER BY program_registrationprofile.id DESC
LIMIT 1
        """ % ESPUser.current_schoolyear()
        #   Try to ensure we don't miss anyone
        students_dict = self.program.students(QObjects=True)
        student_types = ['student_profile']     #   You could add more list names here, but it would get very slow.
        students_Q = Q()
        for student_type in student_types:
            students_Q = students_Q | students_dict[student_type]
        students = ESPUser.objects.filter(students_Q).distinct()
        data = students.extra({'grade': grade_query}).values_list('id', 'last_name', 'first_name', 'grade').distinct()
        simplejson.dump(list(data), resp)
        return resp
    
    @aux_call
    @needs_onsite
    def checkin_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        data = ESPUser.objects.filter(userbit__startdate__lte=datetime.now(), userbit__enddate__gte=datetime.now(), userbit__qsc=prog.anchor, userbit__verb__uri='V/Flags/Registration/Attended').values_list('id').distinct()
        simplejson.dump(list(data), resp)
        return resp
        
    @aux_call
    @needs_onsite
    def counts_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        data = ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog).values_list('id', 'enrolled_students')
        simplejson.dump(list(data), resp)
        return resp
    
    @aux_call    
    @needs_onsite
    def rooms_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        data = ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog).select_related('resourceassignment__resource__name').values_list('id', 'resourceassignment__resource__name', 'resourceassignment__resource__num_students')
        simplejson.dump(list(data), resp)
        return resp
    
    @aux_call
    @needs_onsite
    def get_schedule_json(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        result = {'user': None, 'sections': [], 'messages': []}
        try:
            result['user'] = int(request.GET['user'])
        except:
            result['messages'].append('Error: no user specified.')
        if result['user']:
            result['sections'] = list(ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, studentregistration__start_date__lte=datetime.now(), studentregistration__end_date__gte=datetime.now(), studentregistration__relationship__name='Enrolled', studentregistration__user__id=result['user']).values_list('id', flat=True).distinct())
        simplejson.dump(result, resp)
        return resp
        
    @aux_call
    @needs_onsite
    def update_schedule_json(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
        result = {'user': None, 'sections': [], 'messages': []}
        try:
            user = ESPUser.objects.get(id=int(request.GET['user']))
        except:
            user = None
            result['messages'].append('Error: could find user %s' % request.GET.get('user', None))
        try:
            desired_sections = simplejson.loads(request.GET['sections'])
        except:
            result['messages'].append('Error: could not parse requested sections %s' % request.GET.get('sections', None))
            desired_sections = None
            
        #   Check in student, since if they're using this view they must be onsite
        existing_bits = UserBit.valid_objects().filter(user=user, qsc=prog.anchor, verb=GetNode('V/Flags/Registration/Attended'))
        if not existing_bits.exists():
            new_bit, created = UserBit.objects.get_or_create(user=user, qsc=prog.anchor, verb=GetNode('V/Flags/Registration/Attended'))
            
        if user and desired_sections is not None:
            override_full = (request.GET.get("override", "") == "true")
        
            current_sections = list(ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, studentregistration__start_date__lte=datetime.now(), studentregistration__end_date__gte=datetime.now(), studentregistration__relationship__name='Enrolled', studentregistration__user__id=user.id).values_list('id', flat=True).order_by('id').distinct())
            sections_to_remove = ClassSection.objects.filter(id__in=list(set(current_sections) - set(desired_sections)))
            sections_to_add = ClassSection.objects.filter(id__in=list(set(desired_sections) - set(current_sections)))

            failed_add_sections = []
            for sec in sections_to_add:
                if sec.isFull() and not override_full:
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
                        error = sec.cannotAdd(user, not override_full)
                        if not error:
                            reg_result = sec.preregister_student(user, overridefull=override_full)
                            if not reg_result:
                                error = 'Class is currently full.'
                        else:
                            reg_result = False
                        if reg_result:
                            result['messages'].append('Added %s (%s) to %s: %s (%s)' % (user.name(), user.id, sec.emailcode(), sec.title(), sec.id))
                        else:
                            result['messages'].append('Failed to add %s (%s) to %s: %s (%s).  Error was: %s' % (user.name(), user.id, sec.emailcode(), sec.title(), sec.id, error))
        
            result['user'] = user.id
            result['sections'] = list(ClassSection.objects.filter(status__gt=0, parent_class__status__gt=0, parent_class__parent_program=prog, studentregistration__start_date__lte=datetime.now(), studentregistration__end_date__gte=datetime.now(), studentregistration__relationship__name='Enrolled', studentregistration__user__id=result['user']).values_list('id', flat=True).distinct())
        
        simplejson.dump(result, resp)
        return resp
        
    
    """ End of highly model-dependent JSON views    """
    
    @aux_call
    @needs_onsite
    def printschedule_status(self, request, tl, one, two, module, extra, prog):
        resp = HttpResponse(mimetype='application/json')
         
        verb = GetNode('V/Publish/Print')
        if extra and extra != "":
            verb = verb[extra]
        
        qsc = self.program_anchor_cached().tree_create(['Schedule'])
        result = {}

        try:
            user = int(request.GET.get('user', None))
        except:
            result['message'] = "Could not find user %s." % request.GET.get('user', None)
            
        if user:
            user_obj = ESPUser.objects.get(id=user)
            if not UserBit.objects.filter(user__id=user, verb=verb, qsc=qsc).exclude(enddate__lte=datetime.now()).exists():
                newbit = UserBit.objects.create(user=user_obj, verb=verb, qsc=qsc, recursive=False, enddate=datetime.now() + timedelta(days=1))
                result['message'] = "Submitted %s's schedule for printing." % (user_obj.name())
            else:
                result['message'] = "A schedule is already waiting to be printed for %s." % (user_obj.name())
            
        simplejson.dump(result, resp)
        return resp

    @aux_call
    @needs_onsite
    def classchange_grid(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['timeslots'] = prog.getTimeSlots()
        context['printers'] = GetNode('V/Publish/Print').children().values_list('name', flat=True)
        context['program'] = prog
        context['initial_student'] = request.GET.get('student_id', '')
        return render_to_response(self.baseDir()+'ajax_status.html', request, (prog, tl), context)

    @aux_call
    @needs_onsite
    def status(self, request, tl, one, two, module, extra, prog):
        context = {}
        msgs = []
        if request.method == 'POST':
            if 'op' in request.GET and request.GET['op'] == 'add' and 'sec_id' in request.GET:
                try:
                    sec = ClassSection.objects.get(id=request.GET['sec_id'])
                    print 'Got section %s' % sec
                except:
                    sec = None
                user = None
                if sec and 'add_%s' % sec.id in request.POST:
                    try:
                        user_id = int(request.POST['add_%s' % sec.id])
                        user = ESPUser.objects.get(id=user_id)
                        print 'Got user %s' % user
                    except:
                        user = None
                if sec and user:
                    #   Find out what other classes the user was taking during the times of this section
                    removed_classes = []
                    schedule = user.getEnrolledSections(prog)
                    print 'Got schedule %s' % schedule
                    if sec in schedule:
                        #   If they were in the specified section, take them out.
                        sec.unpreregister_student(user)
                        msgs.append('Removed %s (%d) from %s' % (user.name(), user.id, sec))
                    else:
                        #   Otherwise take them out of whatever they were in and put them in.
                        target_times = sec.meeting_times.all().values_list('id', flat=True)
                        for s in schedule:
                            if s.meeting_times.filter(id__in=target_times).count() > 0:
                                s.unpreregister_student(user)
                                msgs.append('Removed %s (%d) from %s' % (user.name(), user.id, s))
                        sec.preregister_student(user, overridefull=True)
                        msgs.append('Added %s (%d) to %s' % (user.name(), user.id, sec))
        context['msgs'] = msgs
        
        reg_counts = prog.student_counts_by_section_id()
        capacity_counts = prog.capacity_by_section_id()
        checkin_counts = prog.checked_in_by_section_id()
        all_sections = prog.sections()
    
        timeslots = []
        for timeslot in prog.getTimeSlots():
            item = {}
            item['timeslot'] = timeslot
            item['sections'] = []
            sections = all_sections.filter(meeting_times=timeslot)
            for sec in sections:
                sect = OnSiteClassList.section_data(sec)
                
                if sec.id in reg_counts and reg_counts[sec.id]:
                    sect['reg_count'] = reg_counts[sec.id]
                else:
                    sect['reg_count'] = 0
                if sec.id in capacity_counts:
                    sect['capacity_count'] = capacity_counts[sec.id]
                else:
                    sect['capacity_count'] = 0
                if sec.id in checkin_counts:
                    sect['checkin_count'] = checkin_counts[sec.id]
                else:
                    sect['checkin_count'] = 0
                
                if sect['capacity_count'] > 0:
                    hue_redness = sect['reg_count'] / float(sect['capacity_count'])
                else:
                    hue_redness = 0.5
                if sect['reg_count'] > 0:
                    lightness = sect['checkin_count'] / float(sect['reg_count'])
                else:
                    lightness = 0.0
                sect['color'] = hsl_to_rgb(min(1.0, 0.4 + 0.6 * hue_redness), 0.8, 0.9 - 0.5 * lightness)
                
                item['sections'].append(sect)
            timeslots.append(item)
        context['timeslots'] = timeslots
        response = render_to_response(self.baseDir()+'status.html', request, (prog, tl), context)
        return response

    @aux_call
    @needs_onsite
    def classList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """
        context = {}
        defaults = {'refresh': 120, 'scrollspeed': 1}
        for key_option in defaults.keys():
            if request.GET.has_key(key_option):
                context[key_option] = request.GET[key_option]
            else:
                context[key_option] = defaults[key_option]

        time_now = datetime.now()

        if 'start' in request.GET:
            curtime = Event.objects.filter(id=request.GET['start'])
        else:
            window_start = time_now + timedelta(-1, 85200)
            curtime = Event.objects.filter(start__gte=window_start).order_by('start')

        if 'end' in request.GET:
            endtime = Event.objects.filter(id=request.GET['end'])
        else:
            endtime = None

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
            if extra == 'unsorted':
                classes = classes.order_by('begin_time', 'id').distinct()
            elif extra == 'by_time':
                classes = classes.order_by('begin_time', 'parent_class__category', 'id').distinct()
            else:
                classes = classes.order_by('parent_class__category', 'begin_time', 'id').distinct()
        
        context.update({'prog': prog, 'current_time': curtime, 'classes': classes, 'one': one, 'two': two})

        if extra == 'unsorted':
            context['use_categories'] = False
        else:
            context['use_categories'] = True
        
        return render_to_response(self.baseDir()+'classlist.html', request, (prog, tl), context)

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

        printers = [ x.name for x in GetNode('V/Publish/Print').children() ]
        
        return render_to_response(self.baseDir()+'allclasslist.html', request, (prog, tl), 
            {'classes': classes, 'prog': self.program, 'one': one, 'two': two, 'categories': categories.values(), 'printers': printers})


        

    class Meta:
        abstract = True



__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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
import logging
logger = logging.getLogger(__name__)
import sys
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.models import User
from django.db.models.query import Q, QuerySet
from django.template.loader import get_template
from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call, meets_cap, no_auth
from esp.program.modules.handlers.onsiteclasslist import OnSiteClassList
from esp.program.models  import ClassSubject, ClassSection, ClassCategories, RegistrationProfile, StudentRegistration, StudentSubjectInterest
from esp.utils.web import render_to_response
from esp.middleware      import ESPError, AjaxError, ESPError_Log, ESPError_NoLog
from esp.users.models    import ESPUser, Permission, Record
from esp.tagdict.models  import Tag
from argcache            import cache_function
from esp.utils.no_autocookie import disable_csrf_cookie_update
from esp.cal.models import Event, EventType
from esp.program.templatetags.class_render import render_class_direct
from esp.middleware.threadlocalrequest import get_current_request
from esp.utils.query_utils import nest_Q


def json_encode(obj):
    if isinstance(obj, ClassSubject):
        return { 'id': obj.id,
                 'title': obj.title,
                 'parent_program': obj.parent_program_id,
                 'category': obj.category,
                 'class_info': obj.class_info,
#                 'allow_lateness': obj.allow_lateness,
                 'grade_min': obj.grade_min,
                 'grade_max': obj.grade_max,
                 'class_size_min': obj.class_size_min,
                 'class_size_max': obj.class_size_max,
                 'schedule': obj.schedule,
                 'prereqs': obj.prereqs,
#                 'requested_special_resources': obj.requested_special_resources,
#                 'directors_notes': obj.directors_notes,
#                 'requested_room': obj.requested_room,
                 'session_count': obj.session_count,
                 'num_students': obj.num_students(),
                 'teachers': obj._teachers,
                 'get_sections': obj._sections,
                 'num_questions': obj.numStudentAppQuestions()
                 }
    elif isinstance(obj, ClassSection):
        return { 'id': obj.id,
                 'status': obj.status,
                 'duration': obj.duration,
                 'get_meeting_times': obj._events,
                 'num_students': obj.num_students(),
                 'capacity': obj.capacity
                 }
    elif isinstance(obj, ClassCategories):
        return { 'id': obj.id,
                 'category': obj.category,
                 'symbol': obj.symbol
                 }
    elif isinstance(obj, Event):
        return { 'id': obj.id,
                 'program': obj.program_id,
                 'start': obj.start,
                 'end': obj.end,
                 'short_description': obj.description,
                 'event_type': obj.event_type,
                 'priority': obj.priority,
                 }
    elif isinstance(obj, EventType):
        return { 'id': obj.id,
                 'description': obj.description
                 }
    elif isinstance(obj, User):
        return { 'id': obj.id,
                 'first_name': obj.first_name,
                 'last_name': obj.last_name,
                 'username': obj.username,
                 }
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        raise TypeError(repr(obj) + " is not JSON serializable")


# student class picker module
class StudentClassRegModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Student Class Registration",
            "link_title": "Sign up for Classes",
            "module_type": "learn",
            "seq": 10,
            "inline_template": "classlist.html",
            "required": True,
            "choosable": 1
            }]

    @property
    def scrmi(self):
        return self.program.studentclassregmoduleinfo

    def students(self, QObject = False):

        Enrolled = Q(studentregistration__relationship__name='Enrolled')
        Par = Q(studentregistration__section__parent_class__parent_program=self.program)
        Unexpired = nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')

        # Force Django to generate two subqueries without joining SRs to SSIs,
        # as efficiently as possible since it's still a big query.
        sr_ids = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=self.program
        ).values('user').distinct()
        ssi_ids = StudentSubjectInterest.valid_objects().filter(
            subject__parent_program=self.program).values('user').distinct()
        any_reg_q = Q(id__in = sr_ids) | Q(id__in = ssi_ids)

        qobjects = {
            'enrolled': Enrolled & Par & Unexpired,
            'classreg': any_reg_q,
        }

        if QObject:
            return qobjects
        else:
            return {k: ESPUser.objects.filter(v).distinct()
                    for k, v in qobjects.iteritems()}

    def studentDesc(self):
        #   Label these heading nicely like the user registration form
        role_choices = ESPUser.getAllUserTypes()
        role_dict = {}
        for item in role_choices:
            role_dict[item[0]] = item[1]

        return {'classreg': """Students who signed up for at least one class""",
                'enrolled': """Students who are enrolled in at least one class"""}

    def isCompleted(self):
        return (len(get_current_request().user.getSectionsFromProgram(self.program)[:1]) > 0)

    def deadline_met(self, extension=None):
        #   Allow default extension to be overridden if necessary
        if extension is not None:
            return super(StudentClassRegModule, self).deadline_met(extension)
        else:
            return super(StudentClassRegModule, self).deadline_met('/Classes')

    def deadline_met_or_lottery_open(self, extension=None):
        #   Allow default extension to be overridden if necessary
        if extension is not None:
            return self.deadline_met(extension)
        else:
            return self.deadline_met(extension) or \
                   super(StudentClassRegModule, self).deadline_met('/Classes/Lottery')

    def prepare(self, context={}):
        user = get_current_request().user
        program = self.program
        scrmi = self.program.studentclassregmoduleinfo
        return self.prepare_static(user, program, context=context, scrm = self)

    @staticmethod
    def prepare_static(user, program, context={}, scrm = ""):
        from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC
        verbs = RTC.getVisibleRegistrationTypeNames(prog=program)
        regProf = RegistrationProfile.getLastForProgram(user, program)
        timeslots = program.getTimeSlots(types=['Class Time Block', 'Compulsory'])
        classList = ClassSection.prefetch_catalog_data(regProf.preregistered_classes(verbs=verbs))

        prevTimeSlot = None
        blockCount = 0

        is_onsite = user.isOnsite(program)
        scrmi = program.studentclassregmoduleinfo

        #   Filter out volunteer timeslots
        timeslots = [x for x in timeslots if x.event_type.description != 'Volunteer']

        schedule = []
        timeslot_dict = {}
        for sec in classList:
            #   Get the verbs all the time in order for the schedule to show
            #   the student's detailed enrollment status.  (Performance hit, I know.)
            #   - Michael P, 6/23/2009
            #   if scrmi.use_priority:
            sec.verbs = sec.getRegVerbs(user, allowed_verbs=verbs)
            sec.verb_names = [v.name for v in sec.verbs]
            sec.is_enrolled = True if "Enrolled" in sec.verb_names else False

            # While iterating through the meeting times for a section,
            # we use this variable to keep track of the first timeslot.
            # In the section_dict appended to timeslot_dict,
            # we save whether or not this is the first timeslot for this
            # section. If it isn't, the student schedule will indicate
            # this, and will not display the option to remove the
            # section. This is to prevent students from removing what
            # they have mistaken to be duplicated classes from their
            # schedules.
            first_meeting_time = True

            for mt in sec.get_meeting_times().order_by('start'):
                section_dict = {'section': sec, 'first_meeting_time': first_meeting_time}
                first_meeting_time = False
                if mt.id in timeslot_dict:
                    timeslot_dict[mt.id].append(section_dict)
                else:
                    timeslot_dict[mt.id] = [section_dict]

        for i in range(len(timeslots)):
            timeslot = timeslots[i]
            daybreak = False
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1
                    daybreak = True

            if timeslot.id in timeslot_dict:
                cls_list = timeslot_dict[timeslot.id]
                doesnt_have_enrollment = not any(sec['section'].is_enrolled
                                                 for sec in cls_list)
                schedule.append((timeslot, cls_list, blockCount + 1,
                                 doesnt_have_enrollment))
            else:
                schedule.append((timeslot, [], blockCount + 1, False))

            prevTimeSlot = timeslot

        context['num_classes'] = len(classList)
        context['timeslots'] = schedule
        context['use_priority'] = scrmi.use_priority
        if scrm:
            context['allow_removal'] = scrm.deadline_met('/Removal')

        return context


    @aux_call
    @needs_student
    def ajax_schedule(self, request, tl, one, two, module, extra, prog):
        import json as json
        from django.template.loader import render_to_string
        context = self.prepare({})
        context['prog'] = self.program
        context['one'] = one
        context['two'] = two
        context['reg_open'] = bool(Permission.user_has_perm(request.user, {'learn':'Student','teach':'Teacher'}[tl]+"/Classes",prog))

        schedule_str = render_to_string('users/student_schedule_inline.html', context)
        script_str = render_to_string('users/student_schedule_inline.js', context)
        json_data = {'student_schedule_html': schedule_str, 'script': script_str}

        #   Look at the 'extra' data and act appropriately:
        #   -   List, query set, or comma-separated ID list of class sections:
        #       Add the buttons for those class sections to the returned data.
        #   -   String 'all':
        #       Add the buttons for all of the student's class sections to the returned data
        #   -   Anything else:
        #       Don't do anything.
        #   Rewrite registration button if a particular section was named.  (It will be in extra).
        sec_ids = []
        if extra == 'all':
            # TODO(benkraft): this branch of the if was broken for 5 years and
            # nobody noticed, so we may be able to remove it entirely.
            sec_ids = self.user.getSections(self.program).values_list('id', flat=True)
        elif isinstance(extra, list) or isinstance(extra, QuerySet):
            sec_ids = list(extra)
        else:
            try:
                sec_ids = [int(x) for x in extra.split(',')]
            except:
                pass

        for sec_id in sec_ids:
            try:
                section = ClassSection.objects.get(id=sec_id)
                cls = section.parent_class
                button_context = {'sec': section, 'cls': cls}
                if section in request.user.getEnrolledSections(self.program):
                    button_context['label'] = 'Registered!'
                    button_context['disabled'] = True
                addbutton_str1 = render_to_string(self.baseDir()+'addbutton_fillslot.html', button_context)
                addbutton_str2 = render_to_string(self.baseDir()+'addbutton_catalog.html', button_context)
                json_data['addbutton_fillslot_sec%d_html' % sec_id] = addbutton_str1
                json_data['addbutton_catalog_sec%d_html' % sec_id] = addbutton_str2
            except Exception, inst:
                raise AjaxError('Encountered an error retrieving updated buttons: %s' % inst)


        return HttpResponse(json.dumps(json_data))

    @staticmethod
    def addclass_logic(request, tl, one, two, module, extra, prog, webapp=False):
        """ Pre-register the student for the class section in POST['section_id'].
            Return True if there are no errors.
        """
        scrmi = prog.studentclassregmoduleinfo

        #   Explicitly set the user's onsiteness, since we refer to it soon.
        if not hasattr(request.user, "onsite_local"):
            request.user.onsite_local = False

        if 'class_id' in request.POST:
            classid = request.POST['class_id']
            sectionid = request.POST['section_id']
        else:
            raise ESPError("We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL.  Also, please make sure that your Web browser has JavaScript enabled.", log=False)

        section = ClassSection.objects.get(id=sectionid)
        if not scrmi.use_priority:
            error = section.cannotAdd(request.user,scrmi.enforce_max, webapp=webapp)
        if scrmi.use_priority or not error:
            cobj = ClassSubject.objects.get(id=classid)
            error = cobj.cannotAdd(request.user,scrmi.enforce_max, webapp=webapp) or section.cannotAdd(request.user, scrmi.enforce_max, webapp=webapp)

        if scrmi.use_priority:
            priority = request.user.getRegistrationPriority(prog, section.meeting_times.all())
        else:
            priority = 1

        if error and not request.user.onsite_local:
            raise ESPError(error, log=False)

        #   Desired priority level is 1 above current max
        if section.preregister_student(request.user, request.user.onsite_local, priority, webapp=webapp):
            return True
        else:
            raise ESPError('According to our latest information, this class is full. Please go back and choose another class.', log=False)

    @aux_call
    @needs_student
    @meets_deadline('/Classes')
    @meets_cap
    def addclass(self, request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """
        if self.addclass_logic(request, tl, one, two, module, extra, prog):
            return self.goToCore(tl)

    @aux_call
    @needs_student
    @meets_deadline('/Classes')
    @meets_cap
    def ajax_addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class and return an updated inline schedule """
        if not request.is_ajax():
            return self.addclass(request, tl, one, two, module, extra, prog)
        try:
            success = self.addclass_logic(request, tl, one, two, module, extra, prog)
            if 'no_schedule' in request.POST:
                resp = HttpResponse(content_type='application/json')
                json.dump({'status': success}, resp)
                return resp
            if success:
                try:
                    #   Rewrite the registration button if possible.  This requires telling
                    #   the ajax_schedule view what section was added/changed.
                    extra = request.POST['section_id']
                except:
                    pass
                return self.ajax_schedule(request, tl, one, two, module, extra, prog)
        except ESPError_NoLog as inst:
            # TODO(benkraft): we shouldn't need to do this.  find a better way.
            raise AjaxError(inst)

    @staticmethod
    def sort_categories(classes, prog):
        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt if hasattr(cls, 'category_txt') else cls.category.category, 'symbol':cls.category.symbol}

        # Is the catalog sorted by category? If so, by which aspect of category?
        # Default is to sort by category symbol
        catalog_sort = 'category__symbol'
        program_sort_fields = Tag.getProgramTag('catalog_sort_fields', prog)
        if program_sort_fields:
            catalog_sort = program_sort_fields.split(',')[0]

        catalog_sort_split = catalog_sort.split('__')
        if catalog_sort_split[0] == 'category' and catalog_sort_split[1] in ['id', 'category', 'symbol']:
            categories_sort = sorted(categories.values(), key = lambda cat: cat[catalog_sort_split[1]])
        else:
            categories_sort = None
        return categories_sort

    @aux_call
    @needs_student
    @meets_deadline('/Classes')
    @meets_cap
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """
        from esp.cal.models import Event

        try:
            extra = int(extra)
        except:
            raise ESPError('Please use the link at the main registration page.', log=False)
        user = request.user
        ts = Event.objects.filter(id=extra, program=prog)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        user_grade = user.getGrade(self.program)
        user.updateOnsite(request)
        is_onsite = user.isOnsite(self.program)

        #   Override both grade limits and size limits during onsite registration
        #   Classes are sorted like the catalog
        if is_onsite and not 'filter' in request.GET:
            classes = list(ClassSubject.objects.catalog(self.program, ts))
        else:
            classes = filter(lambda c: c.grade_min <= user_grade and c.grade_max >= user_grade, list(ClassSubject.objects.catalog(self.program, ts)))
            if user_grade != 0:
                classes = filter(lambda c: c.grade_min <=user_grade and c.grade_max >= user_grade, classes)
            classes = filter(lambda c: not c.isRegClosed(), classes)

        categories_sort = self.sort_categories(classes, self.program)

        return render_to_response(self.baseDir()+'fillslot.html', request, {'classes':    classes,
                                                                            'one':        one,
                                                                            'two':        two,
                                                                            'categories': categories_sort,
                                                                            'timeslot': ts})

    # This function actually renders the catalog
    def catalog_render(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        # using .extra() to select all the category text simultaneously
        classes = ClassSubject.objects.catalog(self.program)

        categories_sort = self.sort_categories(classes, self.program)

        # Allow tag configuration of whether class descriptions get collapsed
        # when the class is full (default: yes)
        collapse_full = Tag.getBooleanTag('collapse_full_classes', prog)
        context = {'classes': classes, 'one': one, 'two': two, 'categories': categories_sort, 'collapse_full': collapse_full}

        scrmi = prog.studentclassregmoduleinfo
        context['register_from_catalog'] = scrmi.register_from_catalog

        prog_color = prog.getColor()
        collapse_full_classes = Tag.getBooleanTag('collapse_full_classes', prog)
        class_blobs = []

        category_header_str = """<hr size="1"/>
    <a name="cat%d"></a>
      <p style="font-size: 1.2em;" class="category">
         %s
      </p>
      <p class="linktop">
         <a href="#top">[ Return to Category List ]</a>
      </p>
"""

        class_category_id = None
        for cls in classes:
            if cls.category.id != class_category_id and categories_sort:
                class_category_id = cls.category.id
                class_blobs.append(category_header_str % (class_category_id, cls.category.category))
            class_blobs.append(render_class_direct(cls))
            class_blobs.append('<br />')
        context['class_descs'] = ''.join(class_blobs)
        #   Include the program explicitly; this is a cached page, without RequestContext
        context['program'] = self.program

        return render_to_response(self.baseDir()+'catalog.html', request, context, use_request_context=False)

    def catalog_javascript(self, request, tl, one, two, module, extra, prog, timeslot=None):
        return render_to_response(self.baseDir()+'catalog_javascript.html', request, {
                'one':        one,
                'two':        two,
                })


    """@cache_control(public=True, max_age=3600)
    def timeslots_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ """Return the program timeslot names for the tabs in the lottery inteface""" """
        # using .extra() to select all the category text simultaneously
        timeslots = self.program.getTimeSlots()

        resp = HttpResponse(content_type='application/json')

        json.dump(list(timeslots), resp, default=json_encode)

        return resp"""


    @cache_control(public=True, max_age=3600)
    @no_auth
    @aux_call
    def catalog_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        # using .extra() to select all the category text simultaneously
        classes = ClassSubject.objects.catalog(self.program)

        resp = HttpResponse(content_type='application/json')

        json.dump(list(classes), resp, default=json_encode)

        return resp

    def catalog_student_count_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        clean_counts = prog.student_counts_by_section_id()
        resp = HttpResponse(content_type='application/json')
        json.dump(clean_counts, resp)
        return resp

    @aux_call
    @needs_student
    @vary_on_cookie
    def catalog_registered_classes_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        reg_bits = StudentRegistration.valid_objects().filter(user=request.user, section__parent_class__parent_program=prog).select_related()

        reg_bits_data = [
            { 'user': b.user.username,
              'section_id': b.section_id,
              'type': b.relationship.name
              }
            for b in reg_bits ]

        resp = HttpResponse(content_type='application/json')
        json.dump(reg_bits_data, resp)
        return resp

    @disable_csrf_cookie_update
    @aux_call
    @no_auth
    @cache_control(public=True, max_age=120)
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)

    @disable_csrf_cookie_update
    @aux_call
    @no_auth
    @cache_control(public=True, max_age=120)
    def catalog_pdf(self, request, tl, one, two, module, extra, prog):
        #   Get the ProgramPrintables module for the program
        from esp.program.modules.handlers.programprintables import ProgramPrintables
        for module in prog.getModules():
            if isinstance(module, ProgramPrintables):
                #   Use it to generate a PDF catalog with the default settings
                return module.coursecatalog(request, tl, one, two, module, extra, prog)
        raise ESPError('Unable to generate a PDF catalog because the ProgramPrintables module is not installed for this program.', log=False)

    @aux_call
    @needs_student
    def class_docs(self, request, tl, one, two, module, extra, prog):
        from esp.qsdmedia.models import Media

        clsid = 0
        if 'clsid' in request.POST:
            clsid = request.POST['clsid']
        else:
            clsid = extra

        classes = ClassSubject.objects.filter(id = clsid)

        target_class = classes[0]

        context = {'cls': target_class, 'module': self}

        return render_to_response(self.baseDir()+'class_docs.html', request, context)

    @staticmethod
    def clearslot_logic(request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and return True if there are no errors """

        #   Get the sections that the student is registered for in the specified timeslot.
        oldclasses = request.user.getSections(prog).filter(meeting_times=extra)
        #   Narrow this down to one class if we're using the priority system.
        if 'sec_id' in request.GET:
            oldclasses = oldclasses.filter(id=request.GET['sec_id'])
        #   Take the student out if constraints allow
        for sec in oldclasses:
            result = sec.cannotRemove(request.user)
            if result and not hasattr(request.user, "onsite_local"):
                return result
            else:
                sec.unpreregister_student(request.user)
        #   Return the ID of classes that were removed.
        return oldclasses.values_list('id', flat=True)

    @aux_call
    @needs_student
    @meets_any_deadline(['/Classes','/Removal'])
    def clearslot(self, request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and go back to the same page """
        result = self.clearslot_logic(request, tl, one, two, module, extra, prog)
        if isinstance(result, basestring):
            raise ESPError(result, log=False)
        else:
            return self.goToCore(tl)

    @aux_call
    @needs_student
    @meets_any_deadline(['/Classes','/Removal'])
    def ajax_clearslot(self,request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and return an updated inline schedule """
        if not request.is_ajax():
            return self.clearslot(request, tl, one, two, module, extra, prog)

        cleared_ids = self.clearslot_logic(request, tl, one, two, module, extra, prog)

        if 'no_schedule' in request.POST:
            resp = HttpResponse(content_type='application/json')
            json.dump({'status': True, 'cleared_ids': cleared_ids}, resp)
            return resp

        if len(cleared_ids) > 0:
            #   The 'extra' value should be the ID list
            return self.ajax_schedule(request, tl, one, two, module, cleared_ids, prog)

    @aux_call
    @no_auth
    def openclasses(self, request, tl, one, two, module, extra, prog):
        """ A publicly viewable version of the onsite class list.
            Should be revisited in the future, as this was a temporary
            hack created for Stanford Splash in fall 2013. """

        module = prog.getModule('OnSiteClassList')
        if module:
            return module.classList_base(request, tl, one, two, module, 'by_time', prog, options={}, template_name='allclass_fragment.html')

        #  Otherwise this will be a 404
        return None

    class Meta:
        proxy = True
        app_label = 'modules'

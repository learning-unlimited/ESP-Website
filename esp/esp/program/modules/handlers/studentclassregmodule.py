
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

import simplejson
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.db.models.query import Q
from django.db.models.query import Q, QuerySet
from django.template.loader import get_template
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.program.modules.handlers.onsiteclasslist import OnSiteClassList
from esp.datatree.models import *
from esp.program.models  import ClassSubject, ClassSection, ClassCategories, RegistrationProfile, ClassImplication, StudentRegistration
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError, AjaxError, ESPError_Log, ESPError_NoLog
from esp.users.models    import ESPUser, Permission, Record
from esp.tagdict.models  import Tag
from esp.cache           import cache_function
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
            }]

    @classmethod
    def extensions(cls):
        return {'scrmi': module_ext.StudentClassRegModuleInfo}


    def students(self, QObject = False):
        from django.db.models import Q

        Enrolled = Q(studentregistration__relationship__name='Enrolled')
        Par = Q(studentregistration__section__parent_class__parent_program=self.program)
        Unexpired = nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')
        
        if QObject:
            retVal = {'enrolled': self.getQForUser(Enrolled & Par & Unexpired), 'classreg': self.getQForUser(Par & Unexpired)}
        else:
            retVal = {'enrolled': ESPUser.objects.filter(Enrolled & Par & Unexpired).distinct(), 'classreg': ESPUser.objects.filter(Par & Unexpired).distinct()}

        allowed_student_types = Tag.getTag("allowed_student_types", target = self.program)
        if allowed_student_types:
            allowed_student_types = allowed_student_types.split(",")
            for stutype in allowed_student_types:
                GroupName = Q(groups__name=stutype)
                if QObject:
                    retVal[stutype] = self.getQForUser(Par & Unexpired & Reg & VerbName & VerbParent)
                else:
                    retVal[stutype] = ESPUser.objects.filter(Par & Unexpired & Reg & GroupName).distinct()

        return retVal

    def studentDesc(self):
        #   Label these heading nicely like the user registration form
        role_choices = ESPUser.getAllUserTypes()
        role_dict = {}
        for item in role_choices:
            role_dict[item[0]] = item[1]
    
        result = {'classreg': """Students who signed up for at least one class""",
                  'enrolled': """Students who are enrolled in at least one class"""}
        allowed_student_types = Tag.getTag("allowed_student_types", target = self.program)
        if allowed_student_types:
            allowed_student_types = allowed_student_types.split(",")
            for stutype in allowed_student_types:
                if stutype in role_dict:
                    result[stutype] = role_dict[stutype]

        return result

    
    def isCompleted(self):
        return (len(get_current_request().user.getSectionsFromProgram(self.program)[:1]) > 0)

    def deadline_met(self, extension=None):
        #   Allow default extension to be overridden if necessary
        if extension is not None:
            return super(StudentClassRegModule, self).deadline_met(extension)
        else:
            return super(StudentClassRegModule, self).deadline_met('/Classes/OneClass')

    def deadline_met_or_lottery_open(self, extension=None):
        #   Allow default extension to be overridden if necessary
        if extension is not None:
            return self.deadline_met(extension)
        else:
            return self.deadline_met(extension) or \
                   super(StudentClassRegModule, self).deadline_met('/Classes/Lottery')

    def prepare(self, context={}):
        from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC
        verbs = RTC.getVisibleRegistrationTypeNames(prog=self.program)
        regProf = RegistrationProfile.getLastForProgram(get_current_request().user, self.program)
        timeslots = self.program.getTimeSlots(types=['Class Time Block', 'Compulsory'])
        classList = ClassSection.prefetch_catalog_data(regProf.preregistered_classes(verbs=verbs))

        prevTimeSlot = None
        blockCount = 0

        if not isinstance(get_current_request().user, ESPUser):
            user = ESPUser(get_current_request().user)
        else:
            user = get_current_request().user
            
        is_onsite = user.isOnsite(self.program)
        scrmi = self.program.getModuleExtension('StudentClassRegModuleInfo')
        # Hack, to hide the Saturday night timeslots from grades 7-8
        if not is_onsite and not user.getGrade() > 8:
            timeslots = [x for x in timeslots if x.start.hour < 19]
        
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
                    
        user_priority = user.getRegistrationPriorities(self.program, [t.id for t in timeslots])
        for i in range(len(timeslots)):
            timeslot = timeslots[i]
            daybreak = False
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1
                    daybreak = True

            if timeslot.id in timeslot_dict:
                cls_list = timeslot_dict[timeslot.id]
                schedule.append((timeslot, cls_list, blockCount + 1, user_priority[i]))
            else:                
                schedule.append((timeslot, [], blockCount + 1, user_priority[i]))

            prevTimeSlot = timeslot
                
        context['num_classes'] = len(classList)
        context['timeslots'] = schedule
        context['use_priority'] = scrmi.use_priority
        context['allow_removal'] = self.deadline_met('/Removal')

        return context


    @aux_call
    @needs_student
    def ajax_schedule(self, request, tl, one, two, module, extra, prog):
        import simplejson as json
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
            sec_ids = user_sections.values_list('id', flat=True)
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

    def addclass_logic(self, request, tl, one, two, module, extra, prog):
        """ Pre-register the student for the class section in POST['section_id'].
            Return True if there are no errors.
        """
        reg_perm = 'Student/Classes'
        scrmi = self.program.getModuleExtension('StudentClassRegModuleInfo')

        if 'prereg_verb' in request.POST:
            proposed_verb = "V/Flags/Registration/%s" % request.POST['prereg_verb']
            if scrmi.use_priority:
                available_verbs = ["%s/%d" % (scrmi.signup_verb.get_uri(), x) for x in xrange(1, scrmi.priority_limit+1)]
            else:
                available_verbs = [scrmi.signup_verb.get_uri()]

            if proposed_verb in available_verbs:
                prereg_verb = proposed_verb
            else:
                prereg_verb = None
                
        else:
            prereg_verb = None
        
        #   Explicitly set the user's onsiteness, since we refer to it soon.
        if not hasattr(request.user, "onsite_local"):
            request.user.onsite_local = False

        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
            sectionid = request.POST['section_id']
        else:
            raise ESPError("We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL.  Also, please make sure that your Web browser has JavaScript enabled.", log=False)

        # Can we register for more than one class yet?
        if (not request.user.onsite_local) and (not Permission.user_has_perm(request.user, reg_perm, prog ) ):
            enrolled_classes = ESPUser(request.user).getEnrolledClasses(prog, request)
            # Some classes automatically register people for enforced prerequisites (i.e. HSSP ==> Spark). Don't penalize people for these...
            classes_registered = 0
            for cls in enrolled_classes:
                reg_verbs = cls.getRegVerbs(request.user)
                is_auto = 0
                for r in reg_verbs:
                    if r == 'Automatic':
                        is_auto = 1
                if not is_auto:
                    classes_registered += 1

            if classes_registered >= 1:
                datestring = ''
                sreg_perms=Permission.objects.filter(user__isnull=True, role__name="Student", permission_type=reg_perm, program=prog)
                if sreg_perms.count() > 0:
                    d = sreg_perms[0].start_date
                    if d.date() == d.today().date():
                        datestring = ' later today'
                    else:
                        datestring = d.strftime(' on %B %d')
                raise ESPError("Currently, you are only allowed to register for one %s class.  Please come back after student registration fully opens%s!" % (prog.niceName(), datestring), log=False)

        section = ClassSection.objects.get(id=sectionid)
        if not scrmi.use_priority:
            error = section.cannotAdd(request.user,self.scrmi.enforce_max)
        if scrmi.use_priority or not error:
            cobj = ClassSubject.objects.get(id=classid)
            error = cobj.cannotAdd(request.user,self.scrmi.enforce_max) or section.cannotAdd(request.user, self.scrmi.enforce_max)

        if scrmi.use_priority:
            priority = request.user.getRegistrationPriority(prog, section.meeting_times.all())
        else:
            priority = 1

        # autoregister for implied classes one level deep. XOR is currently not implemented, but we're not using it yet either.
        auto_classes = []
        blocked_class = None
        cannotadd_error = ''

        for implication in ClassImplication.objects.filter(cls__id=classid, parent__isnull=True):
            if implication.fails_implication(request.user):
                for cls in ClassSubject.objects.filter(id__in=implication.member_id_ints):
                    #   Override size limits on subprogram classes (checkFull=False). -Michael P
                    sec = cls.default_section()
                    if sec.cannotAdd(request.user, checkFull=False):
                        blocked_class = cls
                        cannotadd_error = sec.cannotAdd(request.user, checkFull=False)
                    else:
                        if sec.preregister_student(request.user, overridefull=True, automatic=True, priority=priority, prereg_verb = prereg_verb):
                            auto_classes.append(sec)
                            if implication.operation != 'AND':
                                break
                        else:
                            blocked_class = cls
                    if (blocked_class is not None) and implication.operation == 'AND':
                        break
                if implication.fails_implication(request.user):
                    for sec in auto_classes:
                        sec.unpreregister_student(request.user, prereg_verb = prereg_verb)
                    if blocked_class is not None:
                        raise ESPError('You have no class blocks free for this class during %s! Please go to <a href="%sstudentreg">%s Student Registration</a> and make sure you have time on your schedule for the class "%s." (%s)' % (blocked_class.parent_program.niceName(), blocked_class.parent_program.get_learn_url(), blocked_class.parent_program.niceName(), blocked_class.title(), cannotadd_error), log=False)
                    else:
                        raise ESPError('You have no class blocks free for this class during %s! Please go to <a href="%sstudentreg">%s Student Registration</a> and make sure you have time on your schedule for the class. (%s)' % (prog.niceName(), prog.get_learn_url(), prog.niceName(), cannotadd_error), log=False)
                    
        if error and not request.user.onsite_local:
            raise ESPError(error, log=False)
        
        #   Desired priority level is 1 above current max
        if section.preregister_student(request.user, request.user.onsite_local, priority, prereg_verb = prereg_verb):
            regs = Record.objects.filter(user=request.user, program=prog, event="reg_confirmed")
            if regs.count() == 0 and Tag.getTag('confirm_on_addclass'):
                r = Record.objects.create(user=request.user, program=prog, event="reg_confirmed")
            return True
        else:
            raise ESPError('According to our latest information, this class is full. Please go back and choose another class.', log=False)
    
    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """
        if self.addclass_logic(request, tl, one, two, module, extra, prog):
            return self.goToCore(tl)
            
    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')
    def ajax_addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class and return an updated inline schedule """
        if not request.is_ajax():
            return self.addclass(request, tl, one, two, module, extra, prog)
        try:
            success = self.addclass_logic(request, tl, one, two, module, extra, prog)
            if 'no_schedule' in request.POST:
                resp = HttpResponse(mimetype='application/json')
                simplejson.dump({'status': success}, resp)
                return resp
            if success:
                try:
                    #   Rewrite the registration button if possible.  This requires telling
                    #   the ajax_schedule view what section was added/changed.
                    extra = request.POST['section_id']
                except:
                    pass
                return self.ajax_schedule(request, tl, one, two, module, extra, prog)
        except ESPError_NoLog, inst:
            print inst
            if inst[0]:
                msg = inst[0]
                raise AjaxError(msg)
            else:
                ec = sys.exc_info()[1]
                raise AjaxError(ec[1])

    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """
        from esp.cal.models import Event

        try:
            extra = int(extra)
        except:
            raise ESPError('Please use the link at the main registration page.', log=False)
        user = ESPUser(request.user)        
        ts = Event.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        prereg_url = self.program.get_learn_url() + 'addclass/'
        user_grade = user.getGrade(self.program)
        user.updateOnsite(request)
        is_onsite = user.isOnsite(self.program)
        
        #   Override both grade limits and size limits during onsite registration
        if is_onsite and not request.GET.has_key('filter'):
            classes = list(ClassSubject.objects.catalog(self.program, ts))
        else:
            classes = filter(lambda c: c.grade_min <= user_grade and c.grade_max >= user_grade, list(ClassSubject.objects.catalog(self.program, ts)))
            if Tag.getBooleanTag('hide_full_classes', prog, default=False):
                classes = filter(lambda c: not c.isFull(timeslot=ts, ignore_changes=True), classes)
            if user_grade != 0:
                classes = filter(lambda c: c.grade_min <=user_grade and c.grade_max >= user_grade, classes)
            classes = filter(lambda c: not c.isRegClosed(), classes)

        #   Sort class list
        classes = sorted(classes, key=lambda cls: cls.num_students() - cls.capacity)
        classes = sorted(classes, key=lambda cls: cls.category.category)

        categories = {}

        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt if hasattr(cls, 'category_txt') else cls.category.category}

        return render_to_response(self.baseDir()+'fillslot.html', request, {'classes':    classes,
                                                                            'one':        one,
                                                                            'two':        two,
                                                                            'categories': categories.values(),
                                                                            'timeslot':   ts,
                                                                            'prereg_url': prereg_url})

    # This function actually renders the catalog
    def catalog_render(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        # using .extra() to select all the category text simultaneously
        classes = ClassSubject.objects.catalog(self.program)

        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt if hasattr(cls, 'category_txt') else cls.category.category}
            
        # Allow tag configuration of whether class descriptions get collapsed
        # when the class is full (default: yes)
        collapse_full = ('false' not in Tag.getProgramTag('collapse_full_classes', prog, 'True').lower())
        hide_full = Tag.getBooleanTag('hide_full_classes', prog, False)
        context = {'classes': classes, 'one': one, 'two': two, 'categories': categories.values(), 'hide_full': hide_full, 'collapse_full': collapse_full}

        scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')
        context['register_from_catalog'] = scrmi.register_from_catalog

        prog_color = prog.getColor()
        collapse_full_classes = ('false' not in Tag.getProgramTag('collapse_full_classes', prog, 'True').lower())
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
            if cls.category.id != class_category_id:
                class_category_id = cls.category.id
                class_blobs.append(category_header_str % (class_category_id, cls.category.category))
            class_blobs.append(render_class_direct(cls))
            class_blobs.append('<br />')
        context['class_descs'] = ''.join(class_blobs)
        #   Include the program explicitly; this is a cached page, without RequestContext
        context['program'] = self.program

        return render_to_response(self.baseDir()+'catalog.html', request, context, use_request_context=False)

#def render_class_core_helper(cls, prog=None, scrmi=None, colorstring=None, collapse_full_classes=None):
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

        resp = HttpResponse(mimetype='application/json')
        
        simplejson.dump(list(timeslots), resp, default=json_encode)
        
        return resp"""

    
    @cache_control(public=True, max_age=3600)
    @aux_call
    def catalog_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        # using .extra() to select all the category text simultaneously
        classes = ClassSubject.objects.catalog(self.program)        
        
        resp = HttpResponse(mimetype='application/json')
        
        simplejson.dump(list(classes), resp, default=json_encode)
        
        return resp


    @cache_control(public=True, max_age=3600)
    def catalog_allowed_reg_verbs(self, request, tl, one, two, module, extra, prog, timeslot=None):
        scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')
        signup_verb_uri = scrmi.signup_verb.get_uri().replace('V/Flags/Registration/', '')

        if scrmi.use_priority:
            verb_list = [ "%s/%d" % (signup_verb_uri, x) for x in xrange(1, scrmi.priority_limit+1) ]
        else:
            verb_list = [ signup_verb_uri ]

        resp = HttpResponse(mimetype='application/json')
        simplejson.dump(verb_list, resp)
        return resp

    def catalog_student_count_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        clean_counts = prog.student_counts_by_section_id()
        resp = HttpResponse(mimetype='application/json')
        simplejson.dump(clean_counts, resp)
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
        
        resp = HttpResponse(mimetype='application/json')
        simplejson.dump(reg_bits_data, resp)
        return resp
    
    # This function exists only to apply the @meets_deadline decorator.
    @meets_deadline('/Catalog')
    def catalog_student(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog, after checking the deadline """
        return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)

    # This function gets called and branches off to the two above depending on the user's role
    @disable_csrf_cookie_update
    @aux_call
    @cache_control(public=True, max_age=120)
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Check user role and maybe return the program class catalog """
        return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)

    @disable_csrf_cookie_update
    @aux_call
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
        if request.POST.has_key('clsid'):
            clsid = request.POST['clsid']
        else:
            clsid = extra
            
        classes = ClassSubject.objects.filter(id = clsid)
        
        target_class = classes[0]

        context = {'cls': target_class, 'module': self}
        
        return render_to_response(self.baseDir()+'class_docs.html', request, context)


    def clearslot_logic(self, request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and return True if there are no errors """
        
        #   Get the sections that the student is registered for in the specified timeslot.
        oldclasses = request.user.getSections(prog).filter(meeting_times=extra)
        #   Narrow this down to one class if we're using the priority system.
        if request.GET.has_key('sec_id'):
            oldclasses = oldclasses.filter(id=request.GET['sec_id'])
        #   Take the student out if constraints allow
        for sec in oldclasses:
            result = sec.cannotRemove(request.user)
            if result:
                return result
            else:
                sec.unpreregister_student(request.user)
        #   Return the ID of classes that were removed.
        return oldclasses.values_list('id', flat=True)

    @aux_call
    @needs_student
    @meets_any_deadline(['/Classes/OneClass','/Removal'])
    def clearslot(self, request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and go back to the same page """
        result = self.clearslot_logic(request, tl, one, two, module, extra, prog)
        if isinstance(result, basestring):
            raise ESPError(result, log=False)
        else:
            return self.goToCore(tl)

    @aux_call
    @needs_student
    @meets_any_deadline(['/Classes/OneClass','/Removal'])
    def ajax_clearslot(self,request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and return an updated inline schedule """
        if not request.is_ajax():
            return self.clearslot(request, tl, one, two, module, extra, prog)
        
        cleared_ids = self.clearslot_logic(request, tl, one, two, module, extra, prog)

        if 'no_schedule' in request.POST:
            resp = HttpResponse(mimetype='application/json')
            simplejson.dump({'status': True, 'cleared_ids': cleared_ids}, resp)
            return resp
        
        if len(cleared_ids) > 0:
            #   The 'extra' value should be the ID list
            return self.ajax_schedule(request, tl, one, two, module, cleared_ids, prog)

    def getNavBars(self):
        """ Returns a list of the dictionary to render the class catalog, if it's open """
        if super(StudentClassRegModule, self).deadline_met('/Catalog'):
            return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
                      'text': '%s Catalog' % ( self.program.niceSubName() ) }]
        
        else:
            return []

    @aux_call
    def openclasses(self, request, tl, one, two, module, extra, prog):
        """ A publicly viewable version of the onsite class list. 
            Should be revisited in the future, as this was a temporary
            hack created for Stanford Splash in fall 2013. """

        module = prog.getModule('OnSiteClassList')
        if module:
            return module.classList_base(request, tl, one, two, module, 'by_time', prog, 'allclass_fragment.html')
        
        #  Otherwise this will be a 404
        return None

    class Meta:
        proxy = True


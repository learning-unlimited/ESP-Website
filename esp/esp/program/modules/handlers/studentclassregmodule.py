
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 MIT ESP

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

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.datatree.models import *
from esp.program.models  import ClassSubject, ClassSection, ClassCategories, RegistrationProfile, ClassImplication
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit, User
from django.db.models.query import Q
from django.template.loader import get_template
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from esp.cal.models import Event, EventType
from datetime import datetime
from decimal import Decimal
import simplejson

def json_encode(obj):
    if isinstance(obj, ClassSubject):
        return { 'id': obj.id,
                 'title': obj.anchor.friendly_name,
                 'anchor': obj.anchor_id,
                 'parent_program': obj.parent_program_id,
                 'category': obj.category,
                 'class_info': obj.class_info,
                 'allow_lateness': obj.allow_lateness,
                 'grade_min': obj.grade_min,
                 'grade_max': obj.grade_max,
                 'class_size_min': obj.class_size_min,
                 'class_size_max': obj.class_size_max,
                 'schedule': obj.schedule,
                 'prereqs': obj.prereqs,
                 'requested_special_resources': obj.requested_special_resources,
                 'directors_notes': obj.directors_notes,
                 'requested_room': obj.requested_room,
                 'session_count': obj.session_count,
                 'num_students': obj._num_students,
                 'teachers': obj._teachers,
                 'get_sections': obj._sections,                         
                 }
    elif isinstance(obj, ClassSection):
        return { 'id': obj.id,
                 'anchor': obj.anchor_id,
                 'status': obj.status,
                 'duration': obj.duration,
                 'get_meeting_times': obj._events,
                 'num_students': obj._count_students,
                 'capacity': obj.capacity
                 }
    elif isinstance(obj, ClassCategories):
        return { 'id': obj.id,
                 'category': obj.category,
                 'symbol': obj.symbol
                 }
    elif isinstance(obj, Event):
        return { 'id': obj.id,
                 'anchor': obj.anchor_id,
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
class StudentClassRegModule(ProgramModuleObj, module_ext.StudentClassRegModuleInfo):
    @classmethod
    def module_properties(cls):
        return [ {
            "link_title": "Sign up for Classes",
            "module_type": "learn",
            "seq": 10,
            "required": True,
            "main_call": "classlist"
            }, {
            "link_title": "Sign up for Classes",
            "admin_title": "Sign up for Classes, SoW (StudentClassRegModule)",
            "module_type": "learn2",
            "seq": 10,
            "required": True,
            "main_call": "sowclass"
            } ]

    def extensions(self):
        """ This function gives all the extensions...that is, models that act on the join of a program and module."""
        return []#(., module_ext.StudentClassRegModuleInfo)] # ClassRegModuleInfo has important information for this module


    def students(self, QObject = False):
        from django.db.models import Q
        verb_base = DataTree.get_by_uri('V/Flags/Registration')

        Par = Q(userbit__qsc__parent__parent=self.program.classes_node())
        Reg = QTree(userbit__verb__below = verb_base)
        Unexpired = Q(userbit__enddate__gte=datetime.now()) # Assumes that, for all still-valid reg userbits, we don't care about startdate, and enddate is null.
        
        if QObject:
            return {'classreg': self.getQForUser(Par & Unexpired & Reg)}
        else:
            return {'classreg': User.objects.filter(Par & Unexpired & Reg).distinct()}

    def studentDesc(self):
        return {'classreg': """Students who have have signed up for at least one class."""}
    
    def isCompleted(self):
        return (len(self.user.getSections(self.program)[:1]) > 0)

    def deadline_met(self, extension=None):
        #   Allow default extension to be overridden if necessary
        if extension is not None:
            return super(StudentClassRegModule, self).deadline_met(extension)
        else:
            return super(StudentClassRegModule, self).deadline_met('/Classes/OneClass')

    @needs_student
    def prepare(self, context={}):
        regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
        timeslots = list(self.program.getTimeSlots().order_by('id'))
        classList = ClassSection.prefetch_catalog_data(regProf.preregistered_classes())
        
        prevTimeSlot = None
        blockCount = 0

        if not isinstance(self.user, ESPUser):
            user = ESPUser(self.user)
        else:
            user = self.user
            
        is_onsite = user.isOnsite(self.program)
        scrmi = self.program.getModuleExtension('StudentClassRegModuleInfo')
        
        schedule = []
        timeslot_dict = {}
        for sec in classList:
            #   TODO: Fix this bit (it was broken, and may need additional queries
            #   or a parameter added to ClassRegModuleInfo).
            show_changeslot = False
            
            #   Get the verbs all the time in order for the schedule to show
            #   the student's detailed enrollment status.  (Performance hit, I know.)
            #   - Michael P, 6/23/2009
            #   if scrmi.use_priority:
            sec.verbs = sec.getRegVerbs(user)

            for mt in sec.get_meeting_times():
                section_dict = {'section': sec, 'changeable': show_changeslot}
                if mt.id in timeslot_dict:
                    timeslot_dict[mt.id].append(section_dict)
                else:
                    timeslot_dict[mt.id] = [section_dict]
                    
        for timeslot in timeslots:
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1

            if scrmi.use_priority:
                user_priority = user.getRegistrationPriority([timeslot])
            else:
                user_priority = None

            if timeslot.id in timeslot_dict:
                cls_list = timeslot_dict[timeslot.id]
                schedule.append((timeslot, cls_list, blockCount + 1, user_priority))
            else:                
                schedule.append((timeslot, [], blockCount + 1, user_priority))

            prevTimeSlot = timeslot
                
        context['timeslots'] = schedule
        context['use_priority'] = scrmi.use_priority
        context['allow_removal'] = self.deadline_met('/Removal')

        return context

    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """
        
        reg_verb = GetNode('V/Deadline/Registration/Student/Classes')
        scrmi = self.program.getModuleExtension('StudentClassRegModuleInfo')
        
        #   Explicitly set the user's onsiteness, since we refer to it soon.
        if not hasattr(self.user, "onsite_local"):
            self.user.onsite_local = False

        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
            sectionid = request.POST['section_id']
        else:
            from esp.dblog.models import error
            raise ESPError(False), "We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL.  Also, please make sure that your Web browser has JavaScript enabled."

        enrolled_classes = ESPUser(request.user).getEnrolledClasses(prog, request)

        # Can we register for more than one class yet?
        if (not self.user.onsite_local) and (not UserBit.objects.UserHasPerms(request.user, prog.anchor, reg_verb ) ):
            # Some classes automatically register people for enforced prerequisites (i.e. HSSP ==> Spark). Don't penalize people for these...
            classes_registered = 0
            for cls in enrolled_classes:
                reg_verbs = cls.getRegVerbs(request.user)
                is_auto = 0
                for r in reg_verbs:
                    if r.name == 'Automatic':
                        is_auto = 1
                if not is_auto:
                    classes_registered += 1

            if classes_registered >= 1:
                datestring = ''
                bitlist = UserBit.objects.filter(user__isnull=True, qsc=prog.anchor, verb=reg_verb)
                if len(bitlist) > 0:
                    d = bitlist[0].startdate
                    if d.date() == d.today().date():
                        datestring = ' later today'
                    else:
                        datestring = d.strftime(' on %B %d')
                raise ESPError(False), "Currently, you are only allowed to register for one %s class.  Please come back after student registration fully opens%s!" % (prog.niceName(), datestring)

        cobj = ClassSubject.objects.get(id=classid)
        section = ClassSection.objects.get(id=sectionid)
        if not scrmi.use_priority:
            error = section.cannotAdd(self.user,self.enforce_max,use_cache=False)
        if scrmi.use_priority or not error:
            error = cobj.cannotAdd(self.user,self.enforce_max,use_cache=False)
        
        priority = self.user.getRegistrationPriority(section.meeting_times.all())

        # autoregister for implied classes one level deep. XOR is currently not implemented, but we're not using it yet either.
        auto_classes = []
        blocked_class = None
        cannotadd_error = ''

        for implication in ClassImplication.objects.filter(cls=cobj, parent__isnull=True):
            if implication.fails_implication(self.user):
                for cls in ClassSubject.objects.filter(id__in=implication.member_id_ints):
                    #   Override size limits on subprogram classes (checkFull=False). -Michael P
                    sec = cls.default_section()
                    if sec.cannotAdd(self.user, checkFull=False, use_cache=False):
                        blocked_class = cls
                        cannotadd_error = sec.cannotAdd(self.user, checkFull=False, use_cache=False)
                    else:
                        if sec.preregister_student(self.user, overridefull=True, automatic=True, priority=priority):
                            auto_classes.append(sec)
                            if implication.operation != 'AND':
                                break
                        else:
                            blocked_class = cls
                    if (blocked_class is not None) and implication.operation == 'AND':
                        break
                if implication.fails_implication(self.user):
                    for sec in auto_classes:
                        sec.unpreregister_student(self.user)
                    if blocked_class is not None:
                        raise ESPError(False), 'You have no class blocks free for this class during %s! Please go to <a href="%sstudentreg">%s Student Registration</a> and make sure you have time on your schedule for the class "%s." (%s)' % (blocked_class.parent_program.niceName(), blocked_class.parent_program.get_learn_url(), blocked_class.parent_program.niceName(), blocked_class.title(), cannotadd_error)
                    else:
                        raise ESPError(False), 'You have no class blocks free for this class during %s! Please go to <a href="%sstudentreg">%s Student Registration</a> and make sure you have time on your schedule for the class. (%s)' % (prog.niceName(), prog.get_learn_url(), prog.niceName(), cannotadd_error)
                    
        if error and not self.user.onsite_local:
            raise ESPError(False), error
        
        #   Desired priority level is 1 above current max
        if section.preregister_student(self.user, self.user.onsite_local, False, priority):
            bits = UserBit.objects.filter(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation")).filter(enddate__gte=datetime.now())
            if bits.count() == 0:
                bit = UserBit.objects.create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))

            return self.goToCore(tl) # go to the core view.
        else:
            raise ESPError(False), 'According to our latest information, this class is full. Please go back and choose another class.'

    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """
        from esp.cal.models import Event

        try:
            extra = int(extra)
        except:
            raise ESPError(False), 'Please use the link at the main registration page.'
        user = ESPUser(request.user)        
        ts = Event.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        prereg_url = self.program.get_learn_url() + 'addclass/'
        user_grade = user.getGrade()
        user.updateOnsite(request)
        is_onsite = user.isOnsite(self.program)
        
        #   Override both grade limits and size limits during onsite registration
        if is_onsite:
            classes = list(ClassSubject.objects.catalog(self.program, ts))
        else:
            classes = list(ClassSubject.objects.catalog(self.program, ts).filter(grade_min__lte=user_grade, grade_max__gte=user_grade))
            classes = filter(lambda c: not c.isFull(timeslot=ts), classes)

        categories = {}

        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt if hasattr(cls, 'category_txt') else cls.category.category}

        return render_to_response(self.baseDir()+'fillslot.html', request, (prog, tl), {'classes':    classes,
                                                                                        'one':        one,
                                                                                        'two':        two,
                                                                                        'categories': categories.values(),
                                                                                        'timeslot':   ts,
                                                                                        'prereg_url': prereg_url})
       

    # we can also ``changeslot'', with only minor modifications to the above code...
    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def changeslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to swap a class. Options have either the same name or same timeslot. """
        from esp.cal.models import Event
        
        user = ESPUser(request.user) 
        prereg_url = self.program.get_learn_url() + 'swapclass/' + extra
        user_grade = user.getGrade()
        is_onsite = user.isOnsite(self.program)

        try:
            extra = int(extra)
        except:
            raise ESPError(False), 'Please use the link at the main registration page.'       
        ts = Event.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]
                        
        # Determining the old class, if any.
        v_registered = request.get_node('V/Flags/Registration/Preliminary')
        oldclasses = ClassSubject.objects.filter(parent_program = self.program,
                             anchor__userbit_qsc__verb = v_registered,
                             anchor__userbit_qsc__user = self.user).distinct()
        oldclasses = filter(lambda x: ts in x.all_meeting_times, oldclasses)
        # If there isn't a class to replace, let's silently switch over to regular adding of classes.
        if len(oldclasses) < 1:
            return self.fillslot(request, tl, one, two, module, extra, prog)
        # If there's more than one to replace, we don't know how to handle that.
        if len(oldclasses) > 1:
            raise ESPError(False), 'Sorry, our website doesn\'t know which class in that time slot you want to change! You\'ll have to go back and do it yourself by clearing the time slot first.'
        # Still here? Okay, continue...
        oldclass = oldclasses[0]
        
        # .objects.catalog() uses .extra() to select all the category text simultaneously
        # The "friendly_name bit" is to test for classes with the same title without having to call c.title()

        class_qset = ClassSubject.objects.catalog(self.program).filter( DjangoQ(meeting_times = ts) | DjangoQ(anchor__friendly_name = oldclass.title()) ) # same time or same title

        class_qset = class_qset.filter(grade_min__lte=user_grade, grade_max__gte=user_grade) # filter within grade limits
        classes = [c for c in class_qset if (not c.isFull()) or is_onsite] # show only viable classes

        categories = {}

        for cls in classes:
            categories[cls.parent_category.category_id] = {'id':cls.parent_class.category_id, 'category':cls.category_txt if hasattr(cls, 'category_txt') else cls.parent_class.category.category}
        
        return render_to_response(self.baseDir()+'changeslot.html', request, (prog, tl), {'classes':    classes,
                                                                                        'oldclass':   oldclass,
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
        
        return render_to_response(self.baseDir()+'catalog.html', request, (prog, tl), {'classes': classes,
                                                                                       'one':        one,
                                                                                       'two':        two,
                                                                                       'categories': categories.values()})

    def catalog_javascript(self, request, tl, one, two, module, extra, prog, timeslot=None):
        return render_to_response(self.baseDir()+'catalog_javascript.html', request, (prog, tl), {
                'one':        one,
                'two':        two,
                })
    
    @cache_control(max_age=3600)
    def catalog_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        # using .extra() to select all the category text simultaneously
        classes = ClassSubject.objects.catalog(self.program)        

        resp = HttpResponse()
        
        simplejson.dump(list(classes), resp, default=json_encode)
        
        return resp

    
    # This function exists only to apply the @meets_deadline decorator.
    @meets_deadline('/Catalog')
    def catalog_student(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog, after checking the deadline """
        return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)

    # This function gets called and branches off to the two above depending on the user's role
    @aux_call
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Check user role and maybe return the program class catalog """
        
        user = ESPUser(request.user)
        if user.isTeacher() or user.isAdmin(self.program.anchor):
            return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)
        else:
            return self.catalog_student(request, tl, one, two, module, extra, prog, timeslot)
    
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
        
        return render_to_response(self.baseDir()+'class_docs.html', request, (prog, tl), context)

    @aux_call
    @needs_student
    @meets_any_deadline(['/Classes/OneClass','/Removal'])
    def clearslot(self, request, tl, one, two, module, extra, prog):
        """ Clear the specified timeslot from a student registration and go back to the same page """
        
        #   The registration verb can be anything under this.
        v_registered_base = request.get_node('V/Flags/Registration')
        
        #   This query just gets worse and worse.   -Michael
        #   Maybe a little better with QTree?   -Axiak
        oldclasses = ClassSection.objects.filter(
            QTree(anchor__userbit_qsc__verb__below = v_registered_base),
            meeting_times=extra,
            parent_class__parent_program = self.program,
            anchor__userbit_qsc__user = self.user).distinct()
                             
        #   Narrow this down to one class if we're using the priority system.
        if request.GET.has_key('sec_id'):
            oldclasses = oldclasses.filter(id=request.GET['sec_id'])
                             
        #classes = self.user.getEnrolledClasses()
        class_ids = [c.parent_class.id for c in oldclasses]
        for cls in oldclasses:
            # Make sure deletion doesn't violate any class implications before proceeding
            for implication in ClassImplication.objects.filter(cls__in=class_ids, enforce=True, parent__isnull=True):
                if implication.fails_implication(self.user, without_classes=set([cls.id])):
                    raise ESPError(False), 'This class is required for your %s class "%s"! To remove this class, please remove the one that requires it through <a href="%sstudentreg">%s Student Registration</a>.' % (implication.cls.parent_program.niceName(), implication.cls.title(), implication.cls.parent_program.get_learn_url(), implication.cls.parent_program.niceName())
            cls.unpreregister_student(self.user)
            
            # Undo auto-registrations of sections
            for implication in ClassImplication.objects.filter(cls=cls, enforce=True):
                for auto_class in ClassSubject.objects.filter(id__in=implication.member_id_ints):
                    auto_class.unpreregister_student(self.user)
                        
        return self.goToCore(tl)

    @aux_call
    @needs_student
    @meets_deadline('/Classes/OneClass')
    def swapclass(self, request, tl, one, two, module, extra, prog):
        """ Swaps one class in a timeslot ("extra") for the one in POST.class_id. """
        
        #   Explicitly set the user's onsiteness, since we refer to it soon.
        if not hasattr(self.user, "onsite_local"):
            self.user.onsite_local = False
        
        v_registered = request.get_node('V/Flags/Registration/Preliminary')
        v_auto = request.get_node('V/Flags/Registration/Preliminary/Automatic')
        
        # Check if implications are already broken
        broken_implications = False
        already_enrolled = [c.id for c in self.user.getEnrolledClasses()]
        for implication in ClassImplication.objects.filter(cls__in=already_enrolled, enforce=True, parent__isnull=True):
#            break;
            if implication.fails_implication(self.user):
                broken_implications = True
        
        # Determining the old class
        oldclasses = ClassSubject.objects.filter(meeting_times=extra,
                             parent_program = self.program,
                             anchor__userbit_qsc__verb = v_registered,
                             anchor__userbit_qsc__user = self.user).distinct()
        
        if oldclasses.count() > 1:
            raise ESPError(False), 'Sorry, our website doesn\'t know which class in that time slot you want to exchange! You\'ll have to go back and do it yourself by clearing the time slot first.'
        oldclass = oldclasses[0]
        automatic = UserBit.objects.UserHasPerms(self.user, oldclass.anchor, v_auto)
        
        # Determining the new class
        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
        else:
            from esp.dblog.models import error
            raise ESPError(), "We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL.  Also, please make sure that your Web browser has JavaScript enabled."
        
        # Withdrawing from the old class
        oldclass.unpreregister_student(self.user)
        
        # Checking if we can register for the new class
        newclass = ClassSubject.objects.filter(id=classid)[0]
        error = newclass.cannotAdd(self.user, self.enforce_max, use_cache=False)
        if error and not self.user.onsite_local:
            # Undo by re-registering the old class. Theoretically "overridefull" is okay, since they were already registered for oldclass anyway.
            oldclass.preregister_student(self.user, overridefull=True, automatic=automatic)
            oldclass.update_cache_students()
            raise ESPError(False), error
        
        # Attempt to register for the new class
        # Carry over the "automatic" userbit if the new class has the same title.
        if newclass.preregister_student(self.user, self.user.onsite_local, automatic and (newclass.title() == oldclass.title()) ):
            newclass.update_cache_students()
        else:
            oldclass.preregister_student(self.user, overridefull=True, automatic=automatic)
            raise ESPError(False), 'According to our latest information, this class is full. Please go back and choose another class.'
        
        # Did we break an implication? If so, undo! If implications were somehow broken to start with, pretend it's okay.
        if not broken_implications:
            already_enrolled = [c.id for c in self.user.getEnrolledClasses()]
            for implication in ClassImplication.objects.filter(cls__in=already_enrolled, enforce=True, parent__isnull=True):
#                break;
                if implication.fails_implication(self.user):
                    newclass.unpreregister_student(self.user)
                    oldclass.preregister_student(self.user, overridefull=True, automatic=automatic)
                    raise ESPError(False), 'The class you intended to remove is required for your %s class "%s"! To remove this class, please remove the one that requires it through <a href="%sstudentreg">%s Student Registration</a>.' % (implication.cls.parent_program.niceName(), implication.cls.title(), implication.cls.parent_program.get_learn_url(), implication.cls.parent_program.niceName())
        
        return self.goToCore(tl)

    def getNavBars(self):
        """ Returns a list of the dictionary to render the class catalog, if it's open """
        if super(StudentClassRegModule, self).deadline_met('/Catalog'):
            return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
                      'text': '%s Catalog' % ( self.program.niceSubName() ) }]
        
        else:
            return []

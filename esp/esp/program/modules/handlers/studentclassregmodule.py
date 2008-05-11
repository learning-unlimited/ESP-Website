
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.datatree.models import GetNode, DataTree
from esp.program.models  import ClassSubject, ClassSection, ClassCategories, RegistrationProfile, ClassImplication
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit, User
from esp.db.models       import Q
from django.template.loader import get_template
from esp.cal.models import Event

# student class picker module
class StudentClassRegModule(ProgramModuleObj):

    def extensions(self):
        """ This function gives all the extensions...that is, models that act on the join of a program and module."""
        return [('classRegInfo', module_ext.StudentClassRegModuleInfo)] # ClassRegModuleInfo has important information for this module


    def students(self, QObject = False):
        from django.db.models import Q as django_Q

        Par = django_Q(userbit__qsc__parent__parent=self.program.classes_node())
        Conf = django_Q(userbit__verb = GetNode('V/Flags/Registration/Confirmed'))
        Prel = django_Q(userbit__verb = GetNode('V/Flags/Registration/Preliminary'))
        Unexpired = django_Q(userbit__enddate__isnull=True) # Assumes that, for all still-valid reg userbits, we don't care about startdate, and enddate is null.
        
        if QObject:
            return {'classreg': self.getQForUser(Par & Unexpired & (Conf | Prel))}
        else:
            return {'classreg': User.objects.filter(Par & Unexpired & (Conf | Prel)).distinct()}


    def studentDesc(self):
        return {'classreg': """Students who have are enrolled in at least one class."""}
    
    def isCompleted(self):
        self.user = ESPUser(self.user)
        if len(self.user.getEnrolledClasses(self.program)) == 0:
            return False
        return (len(self.user.getEnrolledClasses(self.program)) > 0)

    def deadline_met(self):
        #tmpModule = ProgramModuleObj()
        #tmpModule.__dict__ = self.__dict__
        return super(StudentClassRegModule, self).deadline_met('/Classes/OneClass')

    
    @needs_student
    def prepare(self, context={}):
	regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
	timeslots = list(self.program.getTimeSlots().order_by('id'))
	classList = regProf.preregistered_classes()

        prevTimeSlot = None
        blockCount = 0
        
        user = ESPUser(self.user)
        user_grade = user.getGrade()
        is_onsite = user.isOnsite(self.program)
        
        schedule = []
        timeslot_dict = {}
        for sec in classList:
            class_qset = ClassSubject.objects.catalog(self.program).filter(anchor__friendly_name = sec.title, grade_min__lte=user_grade, grade_max__gte=user_grade)
            show_changeslot = ( len([0 for c in class_qset if (not c.isFull()) or is_onsite]) > 1 ) # Does the class have enough siblings to warrant a "change section" link?
            for mt in sec.meeting_times.all().values('id'):
                timeslot_dict.update({mt['id']: (sec, show_changeslot)})
            
        for timeslot in timeslots:
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1

            if timeslot.id in timeslot_dict:
                schedule.append((timeslot, timeslot_dict[timeslot.id][0], blockCount + 1, timeslot_dict[timeslot.id][1]))
            else:
                schedule.append((timeslot, None, blockCount + 1, False))

            prevTimeSlot = timeslot
                
        context['timeslots'] = schedule
        
	return context

        
    @needs_student
    @meets_deadline('/Classes/OneClass')
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """
        
        reg_verb = GetNode('V/Deadline/Registration/Student/Classes')
        
        #   Explicitly set the user's onsiteness, since we refer to it soon.
        if not hasattr(self.user, "onsite_local"):
            self.user.onsite_local = False

        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
            sectionid = request.POST['section_id']
        else:
            from esp.dblog.models import error
            raise ESPError(), "We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL.  Also, please make sure that your Web browser has JavaScript enabled."

        # Can we register for more than one class yet?
        if (not self.user.onsite_local) and (not UserBit.objects.UserHasPerms(request.user, prog.anchor, reg_verb ) ):
            # Some classes automatically register people for enforced prerequisites (i.e. HSSP ==> Spark). Don't penalize people for these...
            classes_registered = 0
            for cls in ESPUser(request.user).getEnrolledClasses(prog, request):
                if not UserBit.objects.UserHasPerms(request.user, cls.anchor, GetNode('V/Flags/Registration/Preliminary/Automatic' )):
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
        error = cobj.cannotAdd(self.user,self.classRegInfo.enforce_max,use_cache=False)
        
        # autoregister for implied classes one level deep. XOR is currently not implemented, but we're not using it yet either.
        auto_classes = []
        blocked_class = None
        cannotadd_error = ''
        for implication in ClassImplication.objects.filter(cls=cobj, parent__isnull=True):
#            break;
            if implication.fails_implication(self.user):
                for cls in ClassSubject.objects.filter(id__in=implication.member_id_ints):
                    #   Override size limits on subprogram classes (checkFull=False). -Michael P
                    if cls.cannotAdd(self.user, checkFull=False, use_cache=False):
                        blocked_class = cls
                        cannotadd_error = cls.cannotAdd(self.user, checkFull=False, use_cache=False)
                    else:
                        if cls.preregister_student(self.user, overridefull=True, automatic=True):
                            auto_classes.append(cls)
                            if implication.operation != 'AND':
                                break
                        else:
                            blocked_class = cls
                    if (blocked_class is not None) and implication.operation == 'AND':
                        break
                if implication.fails_implication(self.user):
                    for cls in auto_classes:
                        cls.unpreregister_student(self.user)
                    if blocked_class is not None:
                        raise ESPError(False), 'You have no class blocks free for this class during %s! Please go to <a href="%sstudentreg">%s Student Registration</a> and make sure you have time on your schedule for the class "%s." (%s)' % (blocked_class.parent_program.niceName(), blocked_class.parent_program.get_learn_url, blocked_class.parent_program.niceName(), blocked_class.title(), cannotadd_error)
                    else:
                        raise ESPError(False), 'You have no class blocks free for this class during %s! Please go to <a href="%sstudentreg">%s Student Registration</a> and make sure you have time on your schedule for the class. (%s)' % (prog.niceName(), prog.get_learn_url, prog.niceName(), cannotadd_error)
                    
        if error and not self.user.onsite_local:
            raise ESPError(False), error
        if section.preregister_student(self.user, self.user.onsite_local):
            bits = UserBit.objects.filter(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation")).filter(Q(enddate__isnull=True)|Q(enddate__gte=datetime.now()))
            if bits.count() == 0:
                bit = UserBit.objects.create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))

            return self.goToCore(tl) # go to the core view.
        else:
            raise ESPError(False), 'According to our latest information, this class is full. Please go back and choose another class.'


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

        prereg_url = self.program.get_learn_url + 'addclass/'
        user_grade = user.getGrade()
        user.updateOnsite(request)
        is_onsite = user.isOnsite(self.program)
        
        classes = [c for c in ClassSubject.objects.catalog(self.program, ts).filter(grade_min__lte=user_grade, grade_max__gte=user_grade) if (not c.isFull(timeslot=ts)) or is_onsite] 

        #   Override both grade limits and size limits during onsite registration
        if is_onsite:
            classes = list(ClassSubject.objects.catalog(self.program, ts))
        else:
            classes = [c for c in ClassSubject.objects.catalog(self.program, ts).filter(grade_min__lte=user_grade, grade_max__gte=user_grade) if (not c.isFull(timeslot=ts))] 

        categories = {}

        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}

        return render_to_response(self.baseDir()+'fillslot.html', request, (prog, tl), {'classes':    classes,
                                                                                        'one':        one,
                                                                                        'two':        two,
                                                                                        'categories': categories.values(),
                                                                                        'timeslot':   ts,
                                                                                        'prereg_url': prereg_url})
       

    # we can also ``changeslot'', with only minor modifications to the above code...
    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def changeslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to swap a class. Options have either the same name or same timeslot. """
        from esp.cal.models import Event
        
        user = ESPUser(request.user) 
        prereg_url = self.program.get_learn_url + 'swapclass/' + extra
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
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}
        
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
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}
        
        return render_to_response(self.baseDir()+'catalog.html', request, (prog, tl), {'classes': classes,
                                                                                       'one':        one,
                                                                                       'two':        two,
                                                                                       'categories': categories.values()})
    
    # This function exists only to apply the @meets_deadline decorator.
    @meets_deadline('/Catalog')
    def catalog_student(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog, after checking the deadline """
        return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)

    # This function gets called and branches off to the two above depending on the user's role
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Check user role and maybe return the program class catalog """
        
        user = ESPUser(request.user)
        if user.isTeacher() or user.isAdmin(self.program.anchor):
            return self.catalog_render(request, tl, one, two, module, extra, prog, timeslot)
        else:
            return self.catalog_student(request, tl, one, two, module, extra, prog, timeslot)
    

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

    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def clearslot(self, request, tl, one, two, module, extra, prog):
	""" Clear the specified timeslot from a student registration and go back to the same page """
	v_registered = request.get_node('V/Flags/Registration/Preliminary')
	v_auto = request.get_node('V/Flags/Registration/Preliminary/Automatic')
        
        oldclasses = ClassSection.objects.filter(meeting_times=extra,
                             classsubject__parent_program = self.program,
                             anchor__userbit_qsc__verb = v_registered,
                             anchor__userbit_qsc__user = self.user).distinct()
        #classes = self.user.getEnrolledClasses()
        class_ids = [c.id for c in oldclasses]
        for cls in oldclasses:
            # Make sure deletion doesn't violate any class implications before proceeding
            for implication in ClassImplication.objects.filter(cls__in=class_ids, enforce=True, parent__isnull=True):
#                break;
                if implication.fails_implication(self.user, without_classes=set([cls.id])):
                    raise ESPError(False), 'This class is required for your %s class "%s"! To remove this class, please remove the one that requires it through <a href="%sstudentreg">%s Student Registration</a>.' % (implication.cls.parent_program.niceName(), implication.cls.title(), implication.cls.parent_program.get_learn_url, implication.cls.parent_program.niceName())
            cls.unpreregister_student(self.user)
            
            # Undo auto-registrations of sections
            for implication in ClassImplication.objects.filter(cls=cls, enforce=True):
#                break;
                for auto_class in ClassSubject.objects.filter(id__in=implication.member_id_ints):
                    if UserBit.objects.UserHasPerms(request.user, auto_class.anchor, v_auto):
                        auto_class.unpreregister_student(self.user)
	return self.goToCore(tl)

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
        error = newclass.cannotAdd(self.user, self.classRegInfo.enforce_max, use_cache=False)
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
                    raise ESPError(False), 'The class you intended to remove is required for your %s class "%s"! To remove this class, please remove the one that requires it through <a href="%sstudentreg">%s Student Registration</a>.' % (implication.cls.parent_program.niceName(), implication.cls.title(), implication.cls.parent_program.get_learn_url, implication.cls.parent_program.niceName())
        
        return self.goToCore(tl)

    def getNavBars(self):
        """ Returns a list of the dictionary to render the class catalog, if it's open """
        if super(StudentClassRegModule, self).deadline_met('/Catalog'):
            return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
                      'text': '%s Catalog' % ( self.program.niceSubName() ) }]
        
        else:
            return []

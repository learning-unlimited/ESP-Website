from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.datatree.models import GetNode, DataTree
from esp.program.models  import Class, ClassCategories, RegistrationProfile
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit
from esp.db.models       import Q

# student class picker module
class StudentClassRegModule(ProgramModuleObj):

    def students(self, QObject = False):
        from esp.program.models import Class
        Conf = Q(userbit__qsc__parent = self.program.classes_node()) & \
               Q(userbit__verb = GetNode('V/Flags/Registration/Confirmed'))

        Prel = Q(userbit__qsc__parent = self.program.classes_node()) & \
               Q(userbit__verb = GetNode('V/Flags/Registration/Preliminary'))
        
        if QObject:
            return {'classreg': self.getQForUser(Conf | Prel)}
        else:
            return {'classreg': ESPUser.objects.filter((Conf | Prel)).distinct()}


    def studentDesc(self):
        return {'classreg': """Students who have are enrolled in at least one class."""}
    
    def isCompleted(self):
        self.user = ESPUser(self.user)
        if self.user.getEnrolledClasses().count() == 0:
            return False
        return self.user.getEnrolledClasses().filter(parent_program = self.program).count() > 0

    def deadline_met(self):
        #tmpModule = ProgramModuleObj()
        #tmpModule.__dict__ = self.__dict__
        return super(StudentClassRegModule, self).deadline_met('/Classes')

    
    @needs_student
    def prepare(self, context={}):
	regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
	timeslots = list(GetNode(self.program.anchor.full_name()+'/Templates/TimeSlots').children().order_by('id'))
	classList = regProf.preregistered_classes()

        schedule = []
        for timeslot in timeslots:
            newClasses = classList.filter(meeting_times = timeslot)
            if len(newClasses) > 0:
                schedule.append((timeslot, newClasses[0]))
            else:
                schedule.append((timeslot, None))
                
        context['timeslots'] = schedule
        
	return context

    @needs_student
    @meets_deadline('/Classes')
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """

        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
        else:
            from esp.dblog.models import error
            raise ESPError(), "We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL."
            
        cobj = Class.objects.filter(id=classid)[0]
        error = cobj.cannotAdd(self.user)
        if error and not self.user.onsite_local:
            raise ESPError(False), error
        if cobj.preregister_student(self.user, self.user.onsite_local):
            cobj.update_cache_students()
            return self.goToCore(tl) # go to the core view.
        else:
            raise ESPError(False), 'Class is full. Please go back to the catalog and choose another class.'


    @needs_student
    @meets_deadline('/Classes')    
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """
        try:
            extra = int(extra)
        except:
            id = None
            return self.catalog(request, tl, one, two, module, extra, prog)
        
        ts = DataTree.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        return self.catalog(request, tl, one, two, module, extra, prog, timeslot=ts)

    # we can also ``changeslot''
    changeslot = fillslot

    @meets_deadline('/Catalog')
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        
        context = {}
        dt_approved = GetNode( 'V/Flags/Class/Approved' )

        #	You'll notice these are the same; we make no distinction yet.
        #	Only show the approve and edit buttons if you're looking at the whole
        #	catalog as opposed to a particular timeslot.  Only show the buttons
        #	for pre-registering if you're looking at a particular timeslot.
        if timeslot is None:
                prereg_url = None
        else:
                prereg_url = '/' + tl + '/' + prog.url() + '/addclass'

        if timeslot is not None:
            classes = Class.objects.filter(parent_program = self.program, meeting_times = timeslot).order_by('category')
            prereg_url = '/'+tl+'/'+self.program.getUrlBase()+'/addclass'
        else:
            prereg_url = False
            classes = Class.objects.filter(parent_program = self.program).order_by('category')
            
            
        catDict = {}
        clsList = []
        if timeslot is not None:
            for cls in classes:
                if cls.isAccepted():
                    clsList.append({'class':cls,
                                    'errormsg':cls.cannotAdd(self.user)})
                    
                    if not catDict.has_key(cls.category_id):
                        catDict[cls.category_id] = {'category': cls.category.category,
                                                    'id'      : cls.category_id
                                                    }
        else:
            for cls in classes:
                if cls.isAccepted():
                    clsList.append({'class':cls,
                                    'errormsg':None})
                    if not catDict.has_key(cls.category_id):
                        catDict[cls.category_id] = {'category': cls.category.category,
                                                    'id'      : cls.category_id
                                                    }
        catList = []
        for k in catDict.keys():
            catList.append(catDict[k])


        return render_to_response(self.baseDir()+'catalog.html', request, (prog, tl), {'courses':    clsList,
                                                                                       'one':        one,
                                                                                       'two':        two,
                                                                                       'timeslot':   timeslot,
                                                                                       'categories': catList,
                                                                                       'prereg_url':  prereg_url
                                                                             })


    @needs_student
    @meets_deadline('/Classes')    
    def clearslot(self, request, tl, one, two, module, extra, prog):
	""" Clear the specified timeslot from a student registration and go back to the same page """
        from esp.users.models import UserBit
	ts = DataTree.objects.filter(id=extra)[0]
	v_registered = GetNode('V/Flags/Registration/Preliminary')
	
	#	Get list of all pre-registration userbits
	prereg_ubs = UserBit.objects.filter(user=request.user, verb=v_registered)
	
	#	Find the userbits for classes in that timeslot and delete them.
	for ub in prereg_ubs:
            if Class.objects.filter(meeting_times=extra, anchor=ub.qsc).count() > 0:
                cobj = Class.objects.filter(anchor = ub.qsc)
                if len(cobj) > 0:
                    for cls in cobj:
                        cls.update_cache_students()
		ub.delete()



	return self.goToCore(tl)

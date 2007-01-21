from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.datatree.models import GetNode, DataTree
from esp.program.models import Class, ClassCategories, RegistrationProfile
from esp.program.modules import module_ext
from esp.web.data        import render_to_response

# student class picker module
class StudentClassRegModule(ProgramModuleObj):

    def isCompleted(self):
        if self.user.getEnrolledClasses().count() == 0:
            return False
        return self.user.getEnrolledClasses().filter(parent_program = self.program).count() > 0

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
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """

        classid = request.POST['class_id']
        cobj = Class.objects.filter(id=classid)[0]
        error = cobj.cannotAdd(self.user)
        if error:
            assert False, error
        if cobj.preregister_student(self.user):
            return self.goToCore(tl) # go to the core view.
        else:
            assert False, 'Class is full'

    @needs_student
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """
        ts = DataTree.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        return self.catalog(request, tl, one, two, module, extra, prog, timeslot=ts)

    # we can also ``changeslot''
    changeslot = fillslot

    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        
        context = {}
        dt_approved = GetNode( 'V/Flags/Class/Approved' )

        if request.POST:
                for i in [ 'class_id', 'action' ]:
                        if not request.POST.has_key(i):
                                assert False, i
                                #raise Http404()

                clsObj = Class.objects.filter(pk=request.POST['class_id'])[0]

                if self.user.canEdit(clsObj):
                        if request.POST['action'] == 'Edit':
                                clsid = int(request.POST['class_id']) # we have a class
                                clslist = list(Class.objects.filter(id = clsid))
                                if len(clslist) != 1:
                                        assert False, 'Zero (or more than 1) classes match selected ID.'
                                clsobj = clslist[0]
                                prog = clsobj.parent_program
                                two  = prog.anchor.name
                                one  = prog.anchor.parent.name
                                return program_teacherreg2(request, 'teach', one, two, 'teacherreg', '', prog, clsobj)

                if self.user.canAdminister(prog):
                        if request.POST['action'] == 'Accept':
                                clsObj.accept()

                        if request.POST['action'] == 'Reject':
                                clsObj.reject()

                        if request.POST['action'] == 'Change Time':
                                clsObj.setTime(request.POST['event_template'])

        #	You'll notice these are the same; we make no distinction yet.
        #	Only show the approve and edit buttons if you're looking at the whole
        #	catalog as opposed to a particular timeslot.  Only show the buttons
        #	for pre-registering if you're looking at a particular timeslot.
        if timeslot is None:
                can_edit_classes = self.user.canAdminister(prog)
                can_approve_classes = self.user.canAdminister(prog)
                prereg_url = None
        else:
                can_edit_classes = False
                can_approve_classes = False
                prereg_url = '/' + tl + '/' + prog.url() + '/addclass'

        if timeslot is not None:
            classes = Class.objects.filter(parent_program = self.program, meeting_times = timeslot).order_by('category')
            prereg_url = '/'+tl+'/'+self.program.getUrlBase()+'/addclass'
        else:
            prereg_url = False
            classes = Class.objects.filter(parent_program = self.program).order_by('category')
            
        catDict = {}
        clsList = []
        for cls in classes:
            if cls.isAccepted():
                clsList.append({'class':cls,
                                'errormsg':cls.cannotAdd(self.user)})
                catDict[cls.category.id] = {'category': cls.category.category,
                                            'id'      : cls.category.id
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
		ub.delete()

	return self.goToCore(tl)

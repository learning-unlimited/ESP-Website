from django.db import models
from django.contrib.auth.models import User
from esp.cal.models import Event
from esp.datatree.models import DataTree, GetNode
from esp.users.models import ESPUser, UserBit, ContactInfo, StudentInfo, TeacherInfo, EducatorInfo, GuardianInfo
from esp.lib.markdown import markdown
from esp.qsd.models import QuasiStaticData
from esp.lib.EmptyQuerySet import EMPTY_QUERYSET
from datetime import datetime
from esp.program.models import RegistrationProfile,ProgramModule, Program, RegistrationProfile, Class, ClassCategories, ResourceRequest, TeacherParticipationProfile, SATPrepRegInfo
from esp.program.modules import module_ext
from esp.program.modules.base import ProgramModuleObj
from esp.web.navBar import makeNavBar
from esp.cal.models import Event, Series
from esp.qsd.models import QuasiStaticData
from esp.datatree.models import GetNode, DataTree
from esp.miniblog.models import Entry
from esp.dbmail.models import MessageRequest
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC
from datetime import datetime
from django import forms
from esp.program.manipulators import SATPrepInfoManipulator
from django.contrib.auth.models import User
from esp.web.models import NavBarEntry
from esp.web.data import navbar_data, preload_images, render_to_response
from django.contrib.auth.decorators import login_required


# reg profile module
class RegProfileModule(ProgramModuleObj):
    def mainView(self, request, tl, one, two, module, extra, prog):
    	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
	from esp.web.myesp import profile_editor
        role = {'teach': 'teacher','learn': 'student'}[tl]

	response = profile_editor(request, prog, False, role)
	if response == True:
		return program_studentreg(request, tl, one, two, module, extra, prog)

	return response    

class StudentRegCore(ProgramModuleObj):
  
    @login_required
    def mainView(request, tl, one, two, module, extra, prog):
  
    	    """ Display a student reg page """
	    curUser = ESPUser(request.user)
	    context = {}
	    if not curUser.isStudent():
		    return render_to_response('program/not_a_student.html', request, (prog, tl),{})

            modules = prog.getModules(curUser)

	    context['completedAll'] = True
            for module in modules:
                if not module.isCompleted() and module.required:
                    context['completedAll'] = False
                    
	    context['modules'] = prog.getModules(curUser)
	    context['one'] = one
	    context['two'] = two

	    return render_to_response('program/studentreg.html', request, (prog, tl), context)

class TeacherClassRegModule(ProgramModuleObj):
    
    @login_required
    def selectclass(self, request, tl, one, two, module, extra, prog):
	""" Display the registration page to allow a teacher to register for a program """
	# Axiak added user bit requirements
	curUser = ESPUser(request.user)
	if not curUser.isTeacher():
		return render_to_response('errors/program/notateacher.html', {})

	context['one'] = one
	context['two'] = two
	context['teacher'] = request.user
	context['timeslots'] = prog.anchor.tree_create(['Templates', 'TimeSlots']).series_set.all()
	
	clsList = [ x for x in curUser.getEditable(Class) if x.parent_program == prog ]
	
	if len(clsList) == 0:
            return program_teacherreg2(request, tl, one, two, module, extra, prog)
            
	context['classes'] = clsList
	
	return render_to_response('program/selectclass', request, (prog, tl), context)
		
    def teacherreg(self, request, tl, one, two, module, extra, prog, class_obj = None):
        """ Actually load a specific class or a new class for editing"""
        curUser = ESPUser(request.user)
    
        # Axiak added user bit requirements
        if not curUser.isTeacher():
            return render_to_response('errors/program/notateacher', {})
    
        context['one'] = one
        context['two'] = two
        context['oops'] = False
        context['teacher'] = request.user
        v = GetNode('V/Administer/Edit')
        q = prog.anchor
    
        if request.POST.has_key('cname'):
            c_id = int(request.POST['cname'])
            try:
                cobj = Class.objects.get(id=c_id)
            except Class.DoesNotExist:
                raise Http404
        
            if not UserBit.UserHasPerms(request.user, cobj.anchor, v, datetime.now()):
                raise Http404
        else:
            if (class_obj == None):
                cobj = Class()
                cobj.anchor = q.tree_decode(['Classes'])
            else:
                cobj = class_obj
            
        context['course'] = cobj

        res = ResourceRequest.objects.filter(requestor = cobj)
        if res.count() == 0:
            res = ResourceRequest(requestor = cobj)
        else:
            res = res[0]
        
        context['res'] = res

        # teacher will volunteer
        #	participation = TeacherParticipationProfile.objects.filter(program = prog, teacher = request.user)
        #	if participation.count() == 0:
        #		participation = TeacherParticipationProfile(program = prog, teacher = request.user)
        #	else:
        #		participation = participation[0]
        #		
        #	context['participation'] = participation
    
    
        if cobj.id is None: selected_times = []
        else: selected_times = cobj.viable_times.all()
        context['ts'] = [ {'obj': x } for x in list(prog.anchor.tree_create(['Templates','TimeSlots']).children()) ]
        for i in range(len(context['ts'])):
            context['ts'][i]['selected'] = (context['ts'][i]['obj'] in selected_times)
        context['cat'] = list(ClassCategories.objects.all())
        #	assert False, 'about to render teacherreg2'
        return render_to_response('program/teacherreg.html', request, (prog, tl), context)



# student class picker module
class StudentClassRegModule(ProgramModuleObj):
    
    
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
	""" Return the program class catalog """
        
	dt_approved = GetNode( 'V/Flags/Class/Approved' )
        
	curUser = ESPUser(request.user)
	# aseering 8/25/2006: We can post to this page to approve a class, or redirect to an edit page
	
	if request.POST:
            for i in [ 'class_id', 'action' ]:
                if not request.POST.has_key(i):
                    assert False, i
                    #raise Http404()

		clsObj = Class.objects.filter(pk=request.POST['class_id'])[0]
		
		if curUser.canEdit(clsObj):
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

		if curUser.canAdminister(prog):
                    if request.POST['action'] == 'Accept':
                        clsObj.accept()
                    elif request.POST['action'] == 'Reject':
                        clsObj.reject()
                    elif request.POST['action'] == 'Change Time':
                        clsObj.setTime(request.POST['event_template'])
                        
            #	You'll notice these are the same; we make no distinction yet.
            #	Only show the approve and edit buttons if you're looking at the whole
            #	catalog as opposed to a particular timeslot.  Only show the buttons
            #	for pre-registering if you're looking at a particular timeslot.
            if timeslot == None:
		can_edit_classes = curUser.canAdminister(prog)
		can_approve_classes = curUser.canAdminister(prog)
		prereg_url = None
            else:
		can_edit_classes = False
		can_approve_classes = False
		prereg_url = '/' + tl + '/' + prog.url() + '/addclass'


            clas = [ {'class': cls, 'accepted': cls.isAccepted(), 
                      'times': [{'id': vt.id, 'label': vt.friendly_name} for vt in cls.viable_times.all()] }
            for cls in prog.class_set.all().order_by('category')
                if (can_approve_classes or can_edit_classes
                    or UserBit.UserHasPerms(request.user, cls.anchor, dt_approved)
                    and (timeslot == None or (cls.event_template != None and cls.event_template == timeslot ))) ]

            p = one + " " + two
		
            #	assert False, 'About to render catalog'
            return render_to_response('program/catalogue', request, (prog, tl), {'Program': p.replace("_", " "),
                                                                                 'courses': clas ,
                                                                                 'prereg_url': prereg_url,
                                                                                 'timeslot': timeslot,
                                                                                 'tl': tl,
                                                                                 'can_edit_classes': can_edit_classes,
                                                                                 'can_approve_classes': can_approve_classes })
        

        



class TeacherClassRegModule(ProgramModuleObj):
    def extensions(self):
        return [('classRegInfo', module_ext.ClassRegModuleInfo)]

class CreditCardModule(ProgramModuleObj):
    def extensions(self):
        return [('creditCardInfo', module_ext.CreditCardModuleInfo)]

class SATPrepModule(ProgramModuleObj):
    pass


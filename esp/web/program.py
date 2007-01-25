from esp.web.navBar import makeNavBar
from esp.cal.models import Event, Series
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit, ESPUser
from esp.datatree.models import GetNode, DataTree
from esp.miniblog.models import Entry
from esp.program.models import RegistrationProfile, Class, ClassCategories, ResourceRequest, TeacherParticipationProfile, SATPrepRegInfo
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC
from datetime import datetime
from esp.users.models import UserBit
from django import forms

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry
from esp.web.data import navbar_data, preload_images, render_to_response
from django.contrib.auth.decorators import login_required

def program_catalog(request, tl, one, two, module, extra, prog, timeslot=None):
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
				
			if request.POST['action'] == 'Reject':
				clsObj.reject()
			
			if request.POST['action'] == 'Change Time':
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

@login_required
def program_profile(request, tl, one, two, module, extra, prog):
	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
	from esp.web.myesp import profile_editor
	role = {'teach': 'teacher','learn': 'student'}[tl]

	response = profile_editor(request, prog, False, role)
	if response == True:
		return program_studentreg(request, tl, one, two, module, extra, prog)

	return response

@login_required
def program_studentreg(request, tl, one, two, module, extra, prog):
	""" Display a student reg page """
	curUser = ESPUser(request.user)
	context = {}
	if not curUser.isStudent():
		return render_to_response('program/not_a_student.html', request, (prog, tl),{})

	# Create a container that has the boolean 'useTemplate'
	moduleContainer = []
	
	modules = prog.program_modules.filter(module_type = 'student_reg').order_by('seq')

	context['completedAll'] = True
	
	for module in modules:
		completed = program_handler_checks[module.check_call](curUser, prog)
		if not completed and module.required:
			context['completedAll'] = False
			
		moduleContainer = moduleContainer + [ {'moduleObj':   module,
						       'useTemplate': not program_handlers.has_key(module.main_call),
						       'isCompleted': completed,
						       'link':        module.makeLink(curUser, prog)
						       } ]
		if program_handler_prepare.has_key(module.main_call):
			context = program_handler_prepare[module.main_call](curUser, prog, context)
	context['modules'] = moduleContainer
	context['one'] = one
	context['two'] = two

	return render_to_response('program/studentreg.html', request, (prog, tl), context)

@login_required
def program_finishstudentreg(request, tl, one, two, module, extra, prog):
	""" Finish student registration for a program """
	pass
	
@login_required
def program_teacherreg(request, tl, one, two, module, extra, prog):
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
		
def program_teacherreg2(request, tl, one, two, module, extra, prog, class_obj = None):
	""" Actually load a specific class or a new class for editing"""
	curUser = ESPUser(request.user)
	
	# Axiak added user bit requirements
	if not curUser.isTeacher():
		return render_to_response('errors/program/notateacher', {})

	context = {}
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

@login_required
def program_fillslot(request, tl, one, two, module, extra, prog):
	""" Display the page to fill the timeslot for a program """
	#ts = TimeSlot.objects.filter(id=extra)[0]
	ts = DataTree.objects.filter(id=extra)[0]

	return program_catalog(request, tl, one, two, module, extra, prog, timeslot=ts)

@login_required
def program_clearslot(request, tl, one, two, module, extra, prog):
	""" Clear the specified timeslot from a student registration and go back to the same page """
	ts = DataTree.objects.filter(id=extra)[0]
	v_registered = GetNode('V/Flags/Registration/Preliminary')
	
	#	Get list of all pre-registration userbits
	prereg_ubs = UserBit.objects.filter(user=request.user, verb=v_registered)
	
	#	Find the userbits for classes in that timeslot and delete them.
	for ub in prereg_ubs:
		if Class.objects.filter(event_template__id=extra, anchor=ub.qsc).count() > 0:
			ub.delete()

	return program_studentreg(request, tl, one, two, module, extra, prog)


@login_required
def program_addclass(request, tl, one, two, module, extra, prog):
	""" Preregister a student for the specified class, then return to the studentreg page """
	from esp.web.views import program
	
	classid = request.POST['class_id']
	cobj = Class.objects.filter(id=classid)[0]
	if cobj.preregister_student(request.user):
		return program(request, tl, one, two, "studentreg")
	else:
		assert False, 'Class is full'


@login_required
def program_makeaclass(request, tl, one, two, module, extra, prog):
	""" Create a new class """
	from esp.web.views import program

	if not UserBit.UserHasPerms(request.user, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'),datetime.now()):
		return render_to_response('errors/program/notateacher', request, prog, {})

	for thing in ['title', 'class_info', 'class_size_min', 'class_size_max', 'grade_min', 'grade_max', 'Time']:
		if not request.POST.has_key(thing) or request.POST[thing] == None or request.POST[thing] == 'None' or request.POST[thing].strip() == "":
			return program(request, tl, one, two, "teacherreg", extra = "oops")

	if request.POST.has_key('id') and request.POST['id'] != 'None':
		aid = int(request.POST['id'])
	else:
		aid = None

	# Checking to make sure a class of the same title by another teacher does not exist
	tmpclasses = Class.objects.filter(anchor__friendly_name=str(request.POST['title']),parent_program=prog)

	if aid is None and tmpclasses.count() > 0 and not UserBit.UserHasPerms(request.user, tmpclasses[0].anchor, GetNode('V/Flags/Registration/Teacher'), datetime.now()):
		return render_to_response('errors/program/classtitleconflict', request, prog, {})

	if aid is None:
		cobj = Class()
	else:
		theclass = Class.objects.filter(id=aid)
		if theclass == [] or theclass is None:
			cobj = Class()
		else:
			cobj = theclass[0]
			# Enforce permissions
			if not UserBit.UserHasPerms(request.user, cobj.anchor, GetNode('V/Administer/Edit'), datetime.now()): raise Http404
	

	
	title = request.POST['title']

	try:
		cobj.grade_max = int(request.POST["grade_max"])
	except ValueError:
		cobj.grade_max = None

	try:
		cobj.grade_min = int(request.POST["grade_min"])
	except ValueError:
		cobj.grade_min = None
		
	cobj.class_size_min = int(request.POST['class_size_min'])
	cobj.class_size_max = int(request.POST['class_size_max'])
		
	cobj.class_info = request.POST['class_info']
	cobj.message_for_directors = request.POST['message_for_directors']
	cobj.parent_program = prog
	cobj.anchor = prog.anchor.tree_create(['Classes', "".join(title.split(" "))])
	cobj.anchor.friendly_name = title
	cobj.anchor.save()

	time_sets = []
	for id in request.POST.getlist('Time'):
		for x in DataTree.objects.filter(id=int(id)):
			time_sets.append(x)

	if len(time_sets) == 0:
		assert False, "Error: Invalid time_set : " + str(time_sets) + ' ' + str(request.POST['Time'])

	#cobj.event_template = time_sets[0]

	if aid is None:
		# Can edit this class
		v = GetNode( 'V/Administer/Edit')
		ub, created = UserBit.objects.get_or_create(user = request.user, qsc = cobj.anchor, verb = v)
		ub.save()

		# is a teacher of this class
		v = GetNode( 'V/Flags/Registration/Teacher')
		ub, created = UserBit.objects.get_or_create(user = request.user, qsc = cobj.anchor, verb = v)
		ub.save()
	
	#TimeSlot
	cat = ClassCategories.objects.filter(id=request.POST['Category'])[0]
	cobj.category = cat
	cobj.enrollment = 0
	cobj.save()
	cobj.viable_times.clear()
	for t in time_sets:
		cobj.viable_times.add(t)
	cobj.save()

# set resources:
# Need to get this working RSN!
	res = ResourceRequest(requestor = cobj)
#	res.requester = cobj
	
	res.wants_projector = request.POST.has_key('wants_projector')
	res.wants_computer_lab = request.POST.has_key('wants_computer_lab') 
	res.wants_open_space = request.POST.has_key('wants_open_space')

	res.save()


	# teacher will volunteer
#	participation = TeacherParticipationProfile.objects.filter(program = prog, teacher = request.user)
#	if participation.count() == 0:
#		participation = TeacherParticipationProfile(program = prog, teacher = request.user)
#	else:
#		participation = participation[0]
#
#	participation.can_help = request.POST.has_key('can_help')
	

	return render_to_response('program/registered', request, (prog, tl), {'aid': aid})


def validateContactInfo(ci):
	""" Confirm that all necessary contact information is attached to the specified object """
	if ci is None: return False
	if ci.full_name == "" or ci.full_name is None: return False
	if ci.address_street == "" or ci.address_street is None: return False
	if ((ci.phone_day != "" and ci.phone_day is not None)
	    or (ci.phone_cell != "" or ci.phone_cell is not None)
	    and not (ci.phone_even != "" or ci.phone_even is not None)):
		return True
	return False

@login_required
def studentRegDecision(request, tl, one, two, module, extra, prog):
	""" The page that is shown once the user saves their student reg, giving them the option of printing a confirmation """
	curUser = ESPUser(request.user)
	context = {}
	context['one'] = one
	context['two'] = two

	modules = prog.getModules(request.user, tl)
	completedAll = True
	for module in modules:
		if not module.isCompleted():
			completedAll = False
			
	
	if completedAll:
		bit, created = UserBit.objects.get_or_create(user=request.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))

	receipt = 'program/receipts/'+str(prog.id)+'_custom_receipt.html'
	return render_to_response(receipt, request, (prog, tl), context)

@login_required
def program_display_credit(request, tl, one, two, module, extra, prog):
	""" Displays the credit card form to feed to OMAR """
	# Catherine: I've manually hard-coded the amount of the program
	return render_to_response('program/creditcard', request, (prog, tl), {'credit_name': two + ' ' + one, 
							 'one': one,
							 'two': two,
							 'student': request.user,
							 'amount': '30'})

def profile_check(user, prog):
	""" Return true if the profile has been filled out. """
	regProf = RegistrationProfile.getLastForProgram(user, prog)
	return regProf.id is not None

def satprepinfo_check(user, prog):
	satPrep = SATPrepRegInfo.getLastForProgram(user, prog)
	return satPrep.id is not None

def class_check(user, prog):
	""" Return true if there are classes that have been registered. """
	regProf = RegistrationProfile.getLastForProgram(user, prog)
	return len(regProf.preregistered_classes()) > 0


def class_prepare(user, prog, context={}):
	regProf = RegistrationProfile.getLastForProgram(user, prog)
	ts = list(GetNode(prog.anchor.full_name()+'/Templates/TimeSlots').children().order_by('id'))
	pre = regProf.preregistered_classes()
	z = [x.event_template for x in pre]
	prerl = []
	for time in ts:
		then = [x for x in pre if x.event_template == time]
		if then == []: prerl.append((time, None))
		else: prerl.append((time, then[0]))
	context['timeslots'] = prerl
	
	return context


program_handlers = {
		    'finishstudentreg': program_finishstudentreg,
		    'finishedStudent': studentRegDecision,
#		    'catalog': program_catalog
		    }

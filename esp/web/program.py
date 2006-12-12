from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.cal.models import Event, Series
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode, DataTree
from esp.miniblog.models import Entry
from esp.program.models import RegistrationProfile, Class, ClassCategories, ResourceRequest, TeacherParticipationProfile
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC
from datetime import datetime

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry

from esp.web.data import navbar_data, preload_images

from django.contrib.auth.decorators import login_required

def program_catalog(request, tl, one, two, module, extra, prog, timeslot=None):
	""" Return the program class catalog """
	dt_approved = GetNode( 'V/Flags/Class/Approved' )
	# aseering 8/25/2006: We can post to this page to approve a class, or redirect to an edit page
	if request.POST:
		for i in [ 'class_id', 'action' ]:
			if not request.POST.has_key(i):
				assert False, i
				#raise Http404()

		if request.POST['action'] == 'Edit':
			return HttpResponseRedirect('/classes/edit/' + request.POST['class_id'] + '/') # We need to redirect to the class edit page
		
		if request.POST['action'] == 'Accept':
			u = UserBit()
			u.user = None
			u.qsc = Class.objects.filter(pk=request.POST['class_id'])[0].anchor
			u.verb = dt_approved
			u.save()
			
		#	We should be able to reject classes too    -Michael P
		
		#	if request.POST['action'] == 'Reject':
		#		u = UserBit()
		#		u.user = None
		#		u.qsc = Class.objects.filter(pk=request.POST['class_id'])[0].anchor
		#		u.verb = GetNode('V/Rejected')
		#		u.save()


	can_edit_classes = UserBit.UserHasPerms(request.user, prog.anchor, GetNode('V/Administer'))
	can_approve_classes = UserBit.UserHasPerms(request.user, prog.anchor, GetNode('V/Administer'))
	
	clas = [ {'class': x, 'accepted': UserBit.UserHasPerms(request.user, x.anchor, dt_approved) }
		 for x in prog.class_set.all().order_by('category')
		 if (can_edit_classes or can_approve_classes
		 or UserBit.UserHasPerms(request.user, x.anchor, dt_approved) )
		 and (timeslot == None or x.event_template == timeslot) ]

	p = one + " " + two
	return render_to_response('program/catalogue', {'request': request,
							'Program': p.replace("_", " "),
							'courses': clas ,
							'navbar_list': makeNavBar(request.user, prog.anchor),
							'preload_images': preload_images,
							'logged_in': request.user.is_authenticated(),
							'tl': tl,
							'can_edit_classes': can_edit_classes,
							'can_approve_classes': can_approve_classes })

@login_required
def program_profile(request, tl, one, two, module, extra, prog):
	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
	regprof = RegistrationProfile.objects.filter(user=request.user,program=prog)[0]

	context = {'logged_in': request.user.is_authenticated() }
	context['student'] = request.user
	context['one'] = one
	if extra == "oops":
		context['oops'] = True
	context['two'] = two
	context['statenames'] = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL'  ,'IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  ,'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']
	contactInfo = request.user.contactinfo_set.all()
	if len(contactInfo) < 1:
		empty = ContactInfo()
		empty.user = request.user
		context['grad'] = empty
		context['studentc'] = empty
		context['emerg'] = empty
		context['guard'] = empty
		context['navbar_list'] = makeNavBar(request.user, prog.anchor)
		context['preload_images'] =  preload_images
		context['request'] = request
		return render_to_response('users/profile', context)
	contactInfo = contactInfo[0]

	context['grad'] = contactInfo.graduation_year
	context['studentc'] = regprof.contact_student
	context['emerg'] = regprof.contact_emergency
	context['guard'] = regprof.contact_guardian
	context['navbar_list'] = makeNavBar(request.user, prog.anchor)
	context['preload_images'] =  preload_images
	context['request'] = request
	return render_to_response('users/profile', context)

@login_required
def program_studentreg(request, tl, one, two, module, extra, prog):
	""" Display a student reg page """
	curUser = request.user
	regprof = RegistrationProfile.objects.filter(user=curUser,program=prog)
	if regprof.count() < 1:
		regprof = RegistrationProfile()
		regprof.user = curUser
		regprof.program = prog
	else:
		regprof = regprof[0]
	context = {'logged_in': request.user.is_authenticated() }
	context['program'] = one + " " + two
	context['program'] = context['program'].replace("_", " ")
	context['one'] = one
	context['two'] = two
	context['navbar_list'] = makeNavBar(request.user, prog.anchor)
	context['preload_images'] =  preload_images
	profile_done = False
	for thing in [regprof.contact_student, regprof.contact_student, regprof.contact_emergency]:
		if validateContactInfo(thing):
			profile_done = True
			break
	if profile_done: context['profile_graphic'] = "checkmark"
	else: context['profile_graphic'] = "nocheckmark"
	context['student'] = curUser.first_name + " " + curUser.last_name
	ts = list(GetNode('Q/Programs/' + one + '/' + two + '/Templates/TimeSlots').children())

	pre = regprof.preregistered_classes()
	z = [x.event_template for x in pre]
	prerl = []
	for time in ts:
		then = [x for x in pre if x.event_template == time]
		if then == []: prerl.append((time, None))
		else: prerl.append((time, then[0]))
	context['timeslots'] = prerl

	if pre != []: context['select_graphic'] = "checkmark"
	else: context['select_graphic'] = "nocheckmark"


	context['request'] = request
	regprof.save()
	return render_to_response('users/studentreg', context)

@login_required
def program_finishstudentreg(request, tl, one, two, module, extra, prog):
	""" Finish student registration for a program """
	pass
	
@login_required
def program_teacherreg(request, tl, one, two, module, extra, prog):
	""" Display the registration page to allow a teacher to register for a program """
	# Axiak added user bit requirements
	if not UserBit.UserHasPerms(request.user, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'),datetime.now()):
		return render_to_response('errors/program/notateacher', {})


	context = {'logged_in': request.user.is_authenticated() }
	context['navbar_list'] = makeNavBar(request.user, prog.anchor)
	context['preload_images'] =  preload_images
	context['one'] = one
	context['two'] = two
	context['teacher'] = request.user
	context['request'] = request
	context['timeslots'] = prog.anchor.tree_create(['Templates', 'TimeSlots']).series_set.all()
	v = GetNode('V/Administer/Edit')
	q = prog.anchor
	cobj = UserBit.find_by_anchor_perms(Class, request.user, v, q)
	if cobj == [] or cobj is None:
		return program_teacherreg2(request, tl, one, two, module, extra, prog)
	else:
		context['classes'] = cobj
		return render_to_response('program/selectclass', context)
		
def program_teacherreg2(request, tl, one, two, module, extra, prog, class_obj = None):
	""" Actually load a specific class or a new class for editing"""

	# Axiak added user bit requirements
	if not UserBit.UserHasPerms(request.user, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'),datetime.now()):
		return render_to_response('errors/program/notateacher', {})

	context = {'logged_in': request.user.is_authenticated() }
	context['navbar_list'] = makeNavBar(request.user, prog.anchor)
	context['preload_images'] =  preload_images
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
# Again...RSN
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
	for i in range(0,len(context['ts'])):
		context['ts'][i]['selected'] = (context['ts'][i]['obj'] in selected_times)
	context['cat'] = list(ClassCategories.objects.all())
	context['request'] = request
	context['program'] = prog
	#	assert False, 'about to render teacherreg2'
	return render_to_response('program/teacherreg', context)

@login_required
def program_fillslot(request, tl, one, two, module, extra, prog):
	""" Display the page to fill the timeslot for a program """
	#ts = TimeSlot.objects.filter(id=extra)[0]
	ts = DataTree.objects.filter(id=extra)[0]

	return program_catalog(request, tl, one, two, module, extra, prog, timeslot=ts)

@login_required
def program_addclass(request, tl, one, two, module, extra, prog):
	""" Preregister a student for the specified class, then return to the studentreg page """
	classid = request.POST['class']
	cobj = Class.objects.filter(id=classid)[0]
	cobj.preregister_student(request.user)

	from esp.web.views import program

	return program(request, tl, one, two, "studentreg")



@login_required
def program_makeaclass(request, tl, one, two, module, extra, prog):
	""" Create a new class """
	from esp.web.views import program

	if not UserBit.UserHasPerms(request.user, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'),datetime.now()):
		return render_to_response('errors/program/notateacher', {})

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
		return render_to_response('errors/program/classtitleconflict',{})

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

	# Can edit this class
	v = GetNode( 'V/Administer/Edit')
	ub = UserBit()
	ub.user = request.user
	ub.qsc = cobj.anchor
	ub.verb = v
	ub.save()

	# is a teacher of this class
	v = GetNode( 'V/Flags/Registration/Teacher')
	ub = UserBit()
	ub.user = request.user
	ub.qsc = cobj.anchor
	ub.verb = v
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
	

	return render_to_response('program/registered', {'request': request,
							 'logged_in': request.user.is_authenticated(),
							 'navbar_list': makeNavBar(request.user, prog.anchor),
							 'preload_images': preload_images,
							 'aid': aid})

@login_required
def program_updateprofile(request, tl, one, two, module, extra, prog):
	""" Update a user profile """
	from esp.web.views import program

	
	for thing in ['first', 'last', 'email', 'street', 'guard_name', 'emerg_name', 'emerg_street']:
		if not request.POST.has_key(thing) and request.POST[thing].strip() != "":
			return program(request, tl, one, two, "profile", extra = "oops")

	sphone = False
	gphone = False
	ephone = False
	if request.has_key('dobmonth'):
		if len(request.POST['dobmonth']) not in [1,2]:
			return program(request, tl, one, two, "profile", extra = "oops")
	if request.has_key('dobday'):
		if len(request.POST['dobday']) not in [1,2]:
			return program(request, tl, one, two, "profile", extra = "oops")
	if request.has_key('dobyear'):
		if len(request.POST['dobyear']) != 4:
			return program(request, tl, one, two, "profile", extra = "oops")
	for phone in ['phone_even', 'phone_cell', 'phone_day']:
		if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			aphone = request.POST[phone]
			if aphone.strip() == "None": continue
			aphone = aphone.split("-")
			if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				# assert False, 5
				return program(request, tl, one, two, "profile", extra = "oops")
			sphone = True
	for phone in ['guard_phone_day', 'guard_phone_cell', 'guard_phone_even']:
		if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			aphone = request.POST[phone]
			if aphone.strip() == "None": continue
			aphone = aphone.split("-")
			if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				# assert False, 6
				return program(request, tl, one, two, "profile", extra = "oops")
			gphone = True
	for phone in ['emerg_phone_day', 'emerg_phone_cell', 'emerg_phone_even']:
		if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			aphone = request.POST[phone]
			if aphone.strip() == "None": continue
			aphone = aphone.split("-")
			if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				# assert False, 7
				return program(request, tl, one, two, "profile", extra = "oops")
			ephone = True
	if not (sphone and gphone and ephone):
		# assert False, 8
		return program(request, tl, one, two, "profile", extra = "oops")
	curUser = request.user
	regprof = RegistrationProfile.objects.filter(user__exact=curUser,program__exact=prog)
	if len(regprof) < 1:
		regprof = RegistrationProfile()
		regprof.user = curUser
		regprof.program = prog
	else:
		regprof = regprof[0]
	curUser.first_name = request.POST['first']
	curUser.last_name = request.POST['last']
	curUser.email = request.POST['email']
	if regprof.contact_student is None:
		c1 = ContactInfo()
		c1.user = curUser
		c1.save()
	else:
		c1 = regprof.contact_student
	c1.grad = request.POST.get('grad', "")
	c1.e_mail = curUser.email
	c1.full_name = curUser.first_name + " " + curUser.last_name
	c1.address_street = request.POST.get('street', "")
	c1.address_city = request.POST.get('city', "")
	c1.address_state = request.POST.get('state', "")
	c1.address_zip = request.POST.get('zip', "")
	if request.has_key('dobmonth') and request.has_key('dobday') and request.has_key('dobyear'):
		c1.dob =  datetime.date(int(request.POST['dobyear']), int(request.POST['dobmonth']), int(request.POST['dobday']))
	c1.phone_day = request.POST.get('phone_day', "")
	c1.phone_cell = request.POST.get('phone_cell', "")
	c1.phone_even = request.POST.get('phone_even', "")
	c1.save()
	regprof.contact_student = c1	    
	if regprof.contact_guardian is None:
		c2 = ContactInfo()
		c2.user = curUser
		c2.save()
	else:
		c2 = regprof.contact_guardian
	c2.full_name = request.POST.get('guard_name', "")
	c2.e_mail = request.POST.get('guard_email', "")
	q = c2.e_mail
	p = c2.full_name
	c2.phone_day = request.POST.get('guard_phone_day', "")
	c2.phone_cell = request.POST.get('guard_phone_cell', "")
	c2.phone_even = request.POST.get('guard_phone_even', "")
	c2.address_street = c1.address_street
	c2.address_city = c1.address_city
	c2.address_state = c1.address_state
	c2.address_zip = c1.address_zip
	c2.save()
	regprof.contact_guardian = c2
	if regprof.contact_emergency is None:
		c3 = ContactInfo()
		c3.user = curUser
		c3.save()
	else:
		c3 = regprof.contact_emergency
	c3.full_name = request.POST.get('emerg_name', "")
	c3.e_mail = request.POST.get('emerg_email', "")
	c3.address_street = request.POST.get('emerg_street', "")
	c3.address_city = request.POST.get('emerg_city', "")
	c3.address_state = request.POST.get('emerg_state', "")
	c3.address_zip = request.POST.get('emerg_zip', "")
	c3.phone_day = request.POST.get('emerg_phone_day', "")
	c3.phone_cell = request.POST.get('emerg_phone_cell', "")
	c3.phone_even = request.POST.get('emerg_phone_even', "")
	c3.save()
	regprof.contact_emergency = c3	    
	curUser.save()
	regprof.save()
	return program_updateprofile(request, tl, one, two, "studentreg", extra, prog)

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
	curUser = request.user
	regprof = RegistrationProfile.objects.filter(user=curUser,program=prog)
	if regprof.count() < 1:
		regprof = RegistrationProfile()
		regprof.user = curUser
		regprof.program = prog
	else:
		regprof = regprof[0]
	context = {'logged_in': request.user.is_authenticated() }
	context['program'] = one + " " + two
	context['program'] = context['program'].replace("_", " ")
	context['one'] = one
	context['two'] = two
	context['request'] = request
	context['navbar_list'] = makeNavBar(request.user, prog.anchor)
	context['preload_images'] =  preload_images
	profile_done = False
	for thing in [regprof.contact_student, regprof.contact_student, regprof.contact_emergency]:
		if validateContactInfo(thing):
			profile_done = True
			break
	if profile_done:
		context['printConfirm'] = True
		pre = regprof.preregistered_classes()
		if pre != []:
			context['printConfirm'] = True
		else: context['printConfirm'] = False
	else: context['printConfirm'] = False
	return render_to_response('program/savescreen', context)

@login_required
def program_display_credit(request, tl, one, two, module, extra, prog):
	""" Displays the credit card form to feed to OMAR """
	# Catherine: I've manually hard-coded the amount of the program
	return render_to_response('program/creditcard', {'request': request,
							 'logged_in': request.user.is_authenticated(),
							 'navbar_list': makeNavBar(request.user, prog.anchor),
							 'preload_images': preload_images,
							 'credit_name': two + ' ' + one, 
							 'one': one,
							 'two': two,
							 'student': request.user,
							 'amount': '30'})

program_handlers = {'catalog': program_catalog,
		    'profile': program_profile,
		    'studentreg': program_studentreg,
		    'finishstudentreg': program_finishstudentreg,
		    'selectclass': program_teacherreg,
		    'teacherreg': program_teacherreg2,
		    'fillslot': program_fillslot,
		    'addclass': program_addclass,
		    'makeaclass': program_makeaclass,
		    'makecourse': program_makeaclass,
		    'updateprofile': program_updateprofile,
		    'startpay': program_display_credit,
		    'finishedStudent': studentRegDecision, 
		    
		    }

from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from esp.cal.models import Event
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit, ESPUser, TeacherInfo, StudentInfo, EducatorInfo, GuardianInfo
from esp.program.models import RegistrationProfile
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from esp.miniblog.views import preview_miniblog, create_miniblog
from esp.program.models import Program, RegistrationProfile, Class, ClassCategories
from esp.web.views.program import program_teacherreg2
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC
import datetime
from django.contrib.auth.models import User
from esp.middleware import ESPError
from esp.web.models import NavBarEntry
from esp.users.manipulators import UserRegManipulator, UserPasswdManipulator, UserRecoverForm, SetPasswordForm
from esp.web.util.main import navbar_data, preload_images, render_to_response
from django import forms
from esp.program.manipulators import StudentProfileManipulator, TeacherProfileManipulator, GuardianProfileManipulator, EducatorProfileManipulator, UserContactManipulator

def myesp_register(request, module):
	""" Return a user-registration page """
	new_data = request.POST.copy()
	if request.GET.has_key('role'):
		new_data['role'] = request.GET['role']
		
	if request.user.is_authenticated():
		return render_to_response('users/duh', request, GetNode('Q/Web/myesp'), {})
	manipulator = UserRegManipulator()
	return render_to_response('users/newuser.html', request, GetNode('Q/Web/myesp'), {'Problem': False,
						    'form':           forms.FormWrapper(manipulator, new_data, {})})



def myesp_finish(request, module):
	""" Complete a user registration """
	admin_program = Program.objects.filter(anchor = GetNode('Q/Programs/Dummy_Programs/Profile_Storage'))[0]
	if request.POST.has_key('profile_page'):
		
		profile_page =  profile_editor(request, admin_program, False, request.POST['current_role'])
		if profile_page == True:
			return render_to_response('users/regdone', request, GetNode('Q/Web/myesp'), {'finish': True})
		else:
			return profile_page
	
	manipulator = UserRegManipulator()
	new_data = request.POST.copy()
	errors = manipulator.get_validation_errors(new_data)

	if errors:
		return render_to_response('users/newuser.html', request, GetNode('Q/Web/myesp'), {'Problem':        True,
								'form':           forms.FormWrapper(manipulator, new_data, errors)})


	# Does there already exist an account with this e-mail address, used for subscribing to mailing lists?
	if User.objects.filter(email=request.POST['email'], password="emailuser").count() > 0:
		# If so, re-use it
		email_user = User.objects.filter(email=request.POST['email'])[0]
		email_user.username = request.POST['username'].lower()
		email_user.last_name = request.POST['last_name']
		email_user.first_name = request.POST['first_name']
		email_user.set_password(request.POST['password'])
		email_user.save()
		email_user = authenticate(username = request.POST['username'].lower(), password = request.POST['password'])
		login(request, email_user)
		return render_to_response('users/regdone', request, GetNode('Q/Web/myesp'), {})


	# We can't steal an already-existing account, so make a new one
	django_user = User()
	django_user.username = request.POST['username'].lower()
	django_user.last_name = request.POST['last_name']
	django_user.first_name = request.POST['first_name']
	django_user.set_password(request.POST['password'])
	django_user.email = request.POST['email']
	django_user.is_staff = False
	django_user.is_superuser = False
	django_user.save()
	django_user = authenticate(username=request.POST['username'].lower(), password=request.POST['password'])
	login(request, django_user)
	if request.POST.has_key('role'):
		# is a teacher of this class
		v = GetNode( 'V/Flags/UserRole/'+request.POST['role'])
		ub = UserBit()
		ub.user = request.user
		ub.recursive = False
		ub.qsc = GetNode('Q')
		ub.verb = v
		ub.save()
	
	profile_page =  profile_editor(request, admin_program, False, request.POST['role'])
	if profile_page == True:
		return render_to_response('users/regdone', request, GetNode('Q/Web/myesp'), {})
	else:
		return profile_page

       

def myesp_emaillist(request, module):
	""" Present the subscribe-to-emaillist page """
	return render_to_response('users/email', request, GetNode('Q/Web/myesp'), {})

def myesp_emailfin(request, module):
	""" Subscribe a user to an e-mail list """
	if not request.POST.has_key('email'):
		return render_to_response('users/newuser.html', request, GetNode('Q/Web/myesp'), {'Problem': True})
	
	if User.objects.filter(email=request.POST['email']).count() == 0:
		if User.objects.filter(email=request.POST['email']).count() > 0:
			return render_to_response('index.html', request, GetNode('Q/Web/myesp'), {})
			
		email_user = User()
		email_user.email = request.POST['email']
		email_user.username = request.POST['email']
		email_user.password = "emailuser"
		email_user.is_staff = False
		email_user.is_superuser = False
		email_user.save()

	return render_to_response('index.html', request, GetNode('Q/Web/myesp'), {})

def myesp_signout(request, module):
	""" Deauthenticate a user """
	logout(request)
	if request.GET.has_key('redirect'):
		return HttpResponseRedirect(request.GET['redirect']+'?role='+request.GET['role'])
	
	return render_to_response('users/logout', request, GetNode('Q/Web/myesp'), {})

def myesp_login(request, module):
	""" Force a login
	Note that the decorator does this, we're just a redirect function """

	if request.POST.has_key('formURL'):
		formURL = request.POST['formURL']
	else:
		if request.META.has_key('HTTP_REFERER'):
			formURL = request.META['HTTP_REFERER']
		else:
			formURL = '/?next=/'

		urlTest = formURL.split('?next=')

		if len(urlTest) > 1:
			formURL = urlTest[1].split('&')[0]
		try:
			if formURL[-15:] == '/myesp/signout/':
				formURL = '/'
		except Exception:
			pass
		
	if request.POST.has_key('username') and request.POST.has_key('password'):
		user = authenticate(username=request.POST['username'].lower(), password=request.POST['password'])
		# user entered incorrect credentials
					
		if not user:
			return render_to_response('users/login', request, None, {'formURL':formURL,'Problem':True})
		
	else:
		user = None
		return render_to_response('users/login', request, None, {'formURL':formURL,'Problem':True})
	
	if user is not None:
		user.set_password(request.POST['password'])
		user.save()
		login(request, user)
		
	

	return HttpResponseRedirect(formURL)
	#return myesp_logfin(request, module)

def search_for_user(request, user_type='Any'):
	""" Interface to search for a user. If you need a user, just use this.
	  Returns (user or response, user returned?) """

	users = None
	error = False
	QSUsers = None


	# Get the "base list" consisting of all the users of a specific type, or all the users.
	if type(user_type) != str:
		All_Users = user_type
	elif user_type == 'All':
		All_Users = ESPUser.objects.all()
	else:
		if user_type not in ESPUser.getTypes():
			assert False, 'user_type must be one of '+str(ESPUser.getTypes())

		All_Users = ESPUser.getAllOfType(user_type, False)

	if request.GET.has_key('userid'):
		userid = -1
		try:
			userid = int(request.GET['userid'])
		except:
			pass

		QSUsers = All_Users.filter(id = userid)
		
	elif request.GET.has_key('username'):
		QSUsers = All_Users.filter(username__icontains = request.GET['username'])
	elif request.GET.has_key('lastname'):
		QSUsers = All_Users.filter(last_name__icontains = request.GET['lastname'])
	elif request.GET.has_key('firstname'):
		QSUsers = All_Users.filter(first_name__icontains = request.GET['firstname'])


	if QSUsers is None:
		users = None
	else:
		users = [ ESPUser(user) for user in QSUsers ]
		

	if users is not None and len(users) == 0:
		error = True
                users = None
        
        if users is None:
		return (render_to_response('users/usersearch.html', request, None, {'error': error}), False)
        if len(users) == 1:
		return (users[0], True)
        else:
		users.sort()
		return (render_to_response('users/userpick.html', request, None, {'users': users}), False)


@login_required
def myesp_passwd(request, module):
	""" Change password """
	new_data = request.POST.copy()
	manipulator = UserPasswdManipulator(request.user)
	if request.method == "POST":
		errors = manipulator.get_validation_errors(new_data)
		if not errors:
			manipulator.do_html2python(new_data)
			user = authenticate(username=new_data['username'].lower(),
					    password=new_data['password'])
			
			user.set_password(new_data['newpasswd'])
			user.save()
			login(request, user)
			return render_to_response('users/passwd.html', request, GetNode('Q/Web/myesp'), {'Success': True})
	else:
		errors = {}
		
	return render_to_response('users/passwd.html', request, GetNode('Q/Web/myesp'), {'Problem': False,
						    'form':           forms.FormWrapper(manipulator, new_data, errors),
											 'Success': False})


def myesp_passrecover(request, module):
	""" Recover the password for a user """
	from esp.users.models import PersistentQueryFilter
	from django.template import loader
	from esp.db.models import Q
	
	new_data = request.POST.copy()
	manipulator = UserRecoverForm()
	
	
	if request.method == 'POST' and request.POST.has_key('prelim'):
		errors = manipulator.get_validation_errors(new_data)
		if not errors:
			try:
				user = User.objects.get(username = new_data['username'])
			except:
				raise ESPError(), 'Could not find user %s.' % new_data['username']

			user = ESPUser(user)
			user.recoverPassword()

			return render_to_response('users/requestrecover.html', request, GetNode('Q/Web/myesp'),{'Success': True})

	else:
		errors = {}

	return render_to_response('users/requestrecover.html', request, GetNode('Q/Web/myesp'),
				  {'form': forms.FormWrapper(manipulator, new_data, errors)})

def myesp_passemailrecover(request, module):
	new_data = request.POST.copy()
	manipulator = SetPasswordForm()

	success = False
	code = ''

	if request.GET.has_key('code'):
		code = request.GET['code']
	if request.POST.has_key('code'):
		code = request.POST['code']
	
	numusers = User.objects.filter(password = code).count()
	if numusers == 0:
		code = False
	
      	
	
	if request.method == 'POST':
		errors = manipulator.get_validation_errors(new_data)
		if not errors:
			user = User.objects.get(username = new_data['username'].lower())
			user.set_password(new_data['newpasswd'])
			user.save()
			auth_user = authenticate(username = new_data['username'].lower(), password = new_data['newpasswd'])
			login(request, auth_user)
			success = True
			
	else:
		errors = {}
		
	return render_to_response('users/emailrecover.html', request, GetNode('Q/Web/myesp'),
				  {'form': forms.FormWrapper(manipulator, new_data, errors),
				   'code': code,
				   'Success': success})
	

@login_required
def myesp_logfin(request, module):
	""" Display the "You have successfully logged in" page """

	return render_to_response('index.html', request, GetNode('Q/Web/myesp'), {})
	
def myesp_home(request, module):
	""" Draw the ESP home page """
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	return render_to_response('display/battlescreen', request, GetNode('Q/Web/myesp'), {'announcements': ann})

#	Format for battlescreens 			Michael P
#	----------------------------------------------
#	The battle screen template is good for drawing individual blocks of helpful stuff.
#	So, it passes the template an array called blocks.

#	Each variable in the blocks array has:
#	-	title
#	-	array of 'header' html strings 
#		(in case you don't want to use separate sections)
#	-	array of sections

#	Each variable in the sections array has
#	-	header text including links
#	-	array of list items
#	-	list of input items
#	-	footer text including links / form items

#	The list item is displayed with a wide cell on the left followed by a narrow cell on the right.
#	The wide cell is like the name of some object to deal with,
#	and the narrow cell is like the administrative actions that can be applied to the object.
#	For example, the wide cell might have "Michael Price: Audio and Speakerbuilding" and the narrow cell
#	might be "Approve / Reject". 

#	An input item is a plain array of 4 containing
#	-	label text
#	-	text value (request.POST[value] = input_text)
#	-	button label (value)
#	-	form action (what URL the data is submitted to)

#	A list item is a plain array of 3 to 5 containing
#	-	left-hand (wide) cell text 
#	-	left-hand (wide) cell url
#	-	right-hand (narrow) cell html
#	-	OPTIONAL: command string
#	-	OPTIONAL: form post URL

#	That hopefully completes the array structure needed for this thing.


def myesp_battlescreen(request, module, admin_details = False, student_version = False):
	"""This function is the main battlescreen for the teachers. It will go through and show the classes
	that they can edit and display. """

	# request.user just got 1-up'd
	currentUser = ESPUser(request.user)

	if request.POST:
		#	If you clicked a button to approve or reject, first clear the "proposed" bit
		#	by setting the end date to now.
		if request.POST.has_key('command'):
			try:
				# not general yet...but started as 'edit','class','classid'...
				command, objtype, objid = request.POST['command'].split('_')
			except ValueError:
				command = None

			if command == 'edit' and objtype == 'class':
				clsid = int(objid) # we have a class
				clslist = list(Class.objects.filter(id = clsid))
				if len(clslist) != 1:
					assert False, 'Zero (or more than 1) classes match selected ID.'
				clsobj = clslist[0]
				prog = clsobj.parent_program
				two  = prog.anchor.name
				one  = prog.anchor.parent.name
				return program_teacherreg2(request, 'teach', one, two, 'teacherreg', '', prog, clsobj)
	
	# I have no idea what structure this is, but at its simplest level,
	# it's a dictionary
	announcements = preview_miniblog(request)

	usrPrograms = currentUser.getVisible(Program)

	# get a list of editable classes
	if student_version:
		clslist = currentUser.getEnrolledClasses()
	else:
		clslist = currentUser.getEditable(Class)

	fullclslist = {}
	
	# not the most direct way of doing it,
	# but hey, it's O(n) in class #, which
	# is nice.
	for cls in clslist:
		if fullclslist.has_key(cls.parent_program.id):
			fullclslist[cls.parent_program.id].append(cls)
		else:
			fullclslist[cls.parent_program.id] = [cls]
	
	# I don't like adding this second structure...
	# but django templates made me do it!
	responseProgs = []

	if admin_details:
		admPrograms = currentUser.getEditable(Program).order_by('-id')
	else:
		admPrograms = []
	
	for prog in usrPrograms:
		if not fullclslist.has_key(prog.id):
			curclslist = []
		else:
			curclslist = fullclslist[prog.id]
		responseProgs.append({'prog':        prog,
				      'clslist':     curclslist,
				      'shortened':   False,#len(curclslist) > 5,
				      'totalclsnum': len(curclslist)})

	return render_to_response('battlescreens/general.html', request, GetNode('Q/Web/myesp'), {'page_title':    'MyESP: Teacher Home Page',
								 'progList':      responseProgs,
								 'admin_details': admin_details,
								 'admPrograms'  : admPrograms,
								 'student_version': student_version,
								 'announcements': {'announcementList': announcements[:5],
										   'overflowed':       len(announcements) > 5,
										   'total':            len(announcements)}})


@login_required
def myesp_battlescreen_admin(request, module):
	curUser = ESPUser(request.user)
	if curUser.isAdministrator():
		return myesp_battlescreen(request, module, admin_details = True)
	else:
		raise Http404

@login_required
def myesp_battlescreen_student(request, module):
	curUser = ESPUser(request.user)
	if curUser.isStudent():
		return myesp_battlescreen(request, module, student_version = True)
	else:
		raise Http404


@login_required
def myesp_switchback(request, module):
	user = request.user
	user = ESPUser(user)
	user.updateOnsite(request)

	if not user.other_user:
		raise ESPError(), 'You were not another user!'

	return HttpResponseRedirect(user.switch_back(request))

@login_required
def edit_profile(request, module):


	curUser = ESPUser(request.user)

	dummyProgram = Program.objects.get(anchor = GetNode('Q/Programs/Dummy_Programs/Profile_Storage'))
	
	if curUser.isStudent():
		return profile_editor(request, None, True, 'Student')
	
	elif curUser.isTeacher():
		return profile_editor(request, None, True, 'Teacher')
	
	elif curUser.isGuardian():
		return profile_editor(request, None, True, 'Guardian')
	
	elif curUser.isEducator():
		return profile_editor(request, None, True, 'Educator')	

	else:
		return profile_editor(request, None, True, '')

@login_required
def profile_editor(request, prog=None, responseuponCompletion = True, role=''):
	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

	if prog is None:
		prog = Program.objects.get(anchor = GetNode('Q/Programs/Dummy_Programs/Profile_Storage'))
		navnode = GetNode('Q/Web/myesp')
	else:
		navnode = prog
		
	curUser = request.user
	role = role.lower();
	context = {'logged_in': request.user.is_authenticated() }
	context['user'] = request.user
	

	manipulator = {'': UserContactManipulator(),
		       'student': StudentProfileManipulator(),
		       'teacher': TeacherProfileManipulator(),
		       'guardian': GuardianProfileManipulator(),
		       'educator': EducatorProfileManipulator()}[role]
	context['profiletype'] = role

	if request.method == 'POST' and request.POST.has_key('profile_page'):
		new_data = request.POST.copy()
		manipulator.prepare(new_data)
		errors = manipulator.get_validation_errors(new_data)
		if not errors:
			manipulator.do_html2python(new_data)

			regProf = RegistrationProfile.getLastForProgram(curUser, prog)

			regProf.contact_user = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_user, '', curUser)
			regProf.contact_emergency = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_emergency, 'emerg_')
			if role == 'student':
				regProf.student_info = StudentInfo.addOrUpdate(curUser, regProf, new_data)
				regProf.contact_guardian = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_guardian, 'guard_')
			elif role == 'teacher':
				regProf.teacher_info = TeacherInfo.addOrUpdate(curUser, regProf, new_data)
			elif role == 'guardian':
				regProf.teacher_info = GuardianInfo.addOrUpdate(curUser, regProf, new_data)
			elif role == 'educator':
				regProf.educator_info = EducatorInfo.addOrUpdate(curUser, regProf, new_data)
			blah = regProf.__dict__
			regProf.save()

			curUser.first_name = new_data['first_name']
			curUser.last_name  = new_data['last_name']
			curUser.email     = new_data['e_mail']
			curUser.save()
			if responseuponCompletion == True:
				return render_to_response('users/profile_complete.html', request, navnode, {})
			else:
				return True

	else:
		errors = {}
		regProf = RegistrationProfile.getLastForProgram(curUser, prog)
		if regProf.id is None:
			regProf = RegistrationProfile.getLastProfile(curUser)
		new_data = {}
		new_data['first_name'] = curUser.first_name
		new_data['last_name']  = curUser.last_name
		new_data['e_mail']     = curUser.email
		new_data = regProf.updateForm(new_data, role)

	context['request'] = request
	context['form'] = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response('users/profile.html', request, navnode, context)

@login_required
def myesp_onsite(request, module):
	
	user = ESPUser(request.user)
	if not user.isOnsite():
		raise ESPError(False), 'You are not a valid on-site user, please go away.'
	verb = GetNode('V/Registration/OnSite')
	
	progs = UserBit.find_by_anchor_perms(Program, user = user, verb = verb)

	if len(progs) == 1:
		return HttpResponseRedirect('/onsite/%s/main' % progs[0].getUrlBase())
	else:
		navnode = GetNode('Q/Web/myesp')
		return render_to_response('program/pickonsite.html', request, navnode, {'progs': progs})

@login_required
def myesp_battlescreen_teacher(request, module):
	qscs = UserBit.bits_get_qsc(user=request.user, verb=GetNode("V/Flags/UserRole/Teacher"))
	if qscs.count() > 0:
		return myesp_battlescreen(request, module)
	else:
		raise Http404	


myesp_handlers = { 'register': myesp_register,
		   'finish': myesp_finish,
		   'emaillist': myesp_emaillist,
		   'emailfin': myesp_emailfin,
		   'signout': myesp_signout,
		   'login': myesp_login,
		   'logfin': myesp_logfin,
		   'home': myesp_home,
		   'switchback': myesp_switchback,
		   'onsite': myesp_onsite,
		   'passwd': myesp_passwd,
		   'passwdrecover': myesp_passrecover,
		   'recoveremail': myesp_passemailrecover,
		   'student': myesp_battlescreen_student,
		   'teacher': myesp_battlescreen_teacher,
		   'admin': myesp_battlescreen_admin,
		   'profile': edit_profile
		   }

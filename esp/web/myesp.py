from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.cal.models import Event
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit, ESPUser
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from esp.miniblog.views import preview_miniblog, create_miniblog
from esp.program.models import Program, RegistrationProfile, Class, ClassCategories
from esp.web.program import program_teacherreg2
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC
import datetime

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry

from esp.web.data import navbar_data, preload_images


def myesp_register(request, module):
	""" Return a user-registration page """
	if request.user.is_authenticated():
		return render_to_response('users/duh', {'request': request,
							'logged_in': True,
							'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
							'preload_images': preload_images})

	return render_to_response('users/newuser.html', {'request': request,
						    'Problem': False,
						    'logged_in': request.user.is_authenticated(),
						    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
						    'preload_images': preload_images})



def myesp_finish(request, module):
	""" Complete a user registration """

	error_dict = {}
	whitespace = " \t"
	
	""" checking for existence of all post objects... """
	formnames = {'confirm':   'Please enter a confirmation password.',
		     'password':  'Please enter a password.',
		     'username':  'Please enter a valid username.',
		     'email':     'Please enter a valid email address.',
		     'role':      'Please select a valid initial role.',
		     'last_name': 'Please enter a valid last name.',
		     'first_name':'Please enter a valid first name.'}

	for name_error in formnames.items():
		if not request.POST.has_key(name_error[0]) or len(set(request.POST[name_error[0]]) - set(" \t")) == 0:
			if error_dict.has_key(name_error[0]):
				error_dict[name_error[0]].append(name_error[1])
			else:
				error_dict[name_error[0]] = [name_error[1]]


	if not error_dict.has_key('username'):
		errormsgList = ESPUser.isUserNameValid(request.POST['username'], True)
		if errormsgList != True:
			error_dict['username'] = [ ('The chosen username ' + errormsg + '.')
						   for errormsg in errormsgList                ]

	if not error_dict.has_key('password') and not error_dict.has_key('confirm'):
		if request.POST['password'] != request.POST['confirm']:
			error_dict['confirm'] = ['The password and password confirmation must be the same.']
		else:
			errormsgList = ESPUser.isPasswordValid(request.POST['password'])
			if errormsgList != True:
				error_dict['password'] = [ ('The chosen password '+errormsg+'.')
							   for errormsg in errormsgList         ]

	if not error_dict.has_key('role'):
		fixedRole = {request.POST['role'] : ' checked'}
	else:
		fixedRole = {}
		
	if len(error_dict) > 0:
		for name, errors in error_dict.items():
			error_dict[name] = '<br />'.join(errors)
			
		return render_to_response('users/newuser.html', {'request':        request,
							         'Problem':        True,
								 'logged_in':      request.user.is_authenticated(),
								 'navbar_list':    makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
								 'errors':         error_dict,
								 'fixedRole':      fixedRole,
								 'preload_images': preload_images})


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
		return render_to_response('users/regdone', {'request': request,
							    'logged_in': request.user.is_authenticated(),
							    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
							    'preload_images': preload_images})


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
		ub.qsc = GetNode('Q')
		ub.verb = v
		ub.save()
			
	return render_to_response('users/regdone', {'request': request,
						    'logged_in': request.user.is_authenticated(),
						    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
						    'preload_images': preload_images})

       

def myesp_emaillist(request, module):
	""" Present the subscribe-to-emaillist page """
	return render_to_response('users/email', {'request': request,
						  'logged_in': False,
						  'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
						  'preload_images': preload_images})

def myesp_emailfin(request, module):
	""" Subscribe a user to an e-mail list """
	if not request.POST.has_key('email'):
		return render_to_response('users/newuser.html', {'request': request,
							    'Problem': True,
							    'logged_in': request.user.is_authenticated(),
							    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
							    'preload_images': preload_images})
	
	if User.objects.filter(email=request.POST['email']).count() == 0:
		if User.objects.filter(email=request.POST['email']).count() > 0:
			return render_to_response('index.html', {
				'request': request,
				'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
				'preload_images': preload_images,
				'logged_in': False})
			
		email_user = User()
		email_user.email = request.POST['email']
		email_user.username = request.POST['email']
		email_user.password = "emailuser"
		email_user.is_staff = False
		email_user.is_superuser = False
		email_user.save()
		return render_to_response('index.html', {
			'request': request,
			'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
			'preload_images': preload_images,
			'logged_in': False})


		

	
	
def myesp_signout(request, module):
	""" Deauthenticate a user """
	logout(request)
	return render_to_response('users/logout', {'request': request,
						   'logged_in': request.user.is_authenticated(),
						   'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
						   'preload_images': preload_images})

def myesp_login(request, module):
	""" Force a login
	Note that the decorator does this, we're just a redirect function """

	if request.POST.has_key('username') and request.POST.has_key('password'):
		user = authenticate(username=request.POST['username'].lower(), password=request.POST['password'])
	else:
		user = None
	
	if user is not None:
		user.set_password(request.POST['password'])
		user.save()
		login(request, user)

	return HttpResponseRedirect("/")
	#return myesp_logfin(request, module)

@login_required
def myesp_logfin(request, module):
	""" Display the "You have successfully logged in" page """

	return render_to_response('index.html', {'request': request,
						 'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
						 'preload_images': preload_images,
						 'logged_in': True
						 })
	
def myesp_home(request, module):
	""" Draw the ESP home page """
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	return render_to_response('display/battlescreen', {'request': request,
							   'announcements': ann,
							   'logged_in': request.user.is_authenticated() })

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

@login_required
def myesp_battlescreen_student(request, module):
	curUser = request.user

	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	
	programs_current = UserBit.find_by_anchor_perms(Program, curUser, GetNode('V/Flags/Public'));
	
	signup_sections = []
	
	for p in programs_current:
		signup_sections.append({'header' : str(p), 
								'items' : [['Information Page', '/learn/' + p.url() + '/index.html', ''],
										['Class Catalog', '/learn/' + p.url() + '/catalog/', ''],
										['Register for Classes', '/learn/' + p.url() + '/studentreg/', 'Help']]
								})
	
	block_ann = 	preview_miniblog(request, 'learn')
				
	block_signup =  {	'title' : 'Register For ESP Programs',
						'headers' : ['Follow the links below to get started.'],
						'sections' : signup_sections
					}
					
	#	The survey engine doesn't exist yet, and that's why the URLs are None.
	block_surveys = {	'title' : 'Online Surveys',
						'headers' : ['We\'re looking for your feedback so we can improve:'],
						'sections' : 
							[{	'header' : 'Splash Fall 2005',
								'items' : 	[['General Survey', None, ''],
											['Class 1 Survey', None, ''],
											['Class 2 Survey', None, '']]
							},
							{	'header' : 'Delve 2005 - 2006',
								'items' :	[['General Survey', None, '']]
							}]
					}
						
	blocks = [block_ann, block_signup, block_surveys]
	welcome_msg = 'This is your ESP "battle screen," from which you can sign up for our programs, get in touch with teachers and administrators, and review your history of interactions with ESP.'
	
	return render_to_response('battlescreens/general', {'request': request,
							   'blocks': blocks,
							   'page_title': 'MyESP: Student Home Page',
							   'navbar_list': makeNavBar(request.user, GetNode('Q/Program/')),
							   'welcome_msg': welcome_msg,
							   'logged_in': request.user.is_authenticated() }) 

@login_required
def myesp_battlescreen_teacher(request, module):
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
	
	for prog in usrPrograms:
		if not fullclslist.has_key(prog.id):
			curclslist = []
		else:
			curclslist = fullclslist[prog.id]
		responseProgs.append({'prog':        prog,
				      'clslist':     curclslist[:5],
				      'shortened':   len(curclslist) > 5,
				      'totalclsnum': len(curclslist)})

	return render_to_response('battlescreens/general.html', {'request':       request,
								 'page_title':    'MyESP: Teacher Home Page',
								 'navbar_list':   makeNavBar(request.user, GetNode('Q/Program')),
								 'logged_in':     request.user.is_authenticated(),
								 'progList':      responseProgs,
								 'announcements': {'announcementList': announcements[:5],
										   'overflowed':       len(announcements) > 5,
										   'total':            len(announcements)}})
								 

@login_required							   
def myesp_battlescreen_admin(request, module):
	curUser = request.user
	
	block_ann = preview_miniblog(request, 'teach')
	
	#	Admins see: read announcements, post announcements, approve/reject classes, program administration, create program
	
	if request.POST:
		#	If you clicked a button to approve or reject, first clear the "proposed" bit
		#	by setting the end date to now.
		if request.POST.has_key('action'):
			if (request.POST['action'] == 'Approve' or request.POST['action'] == 'Reject'):
				u = UserBit()
				u.user = None
				u.end_date = datetime.now()
				u.qsc = Class.objects.filter(pk=request.POST['class_id'])[0].anchor
				u.verb = GetNode('V/Flags/Class/Proposed')
				u.save()
			#	And, if the class was approved, grant the Approved verb to it.		
			if request.POST['action'] == 'Approve':
				u = UserBit()
				u.user = None
				u.qsc = Class.objects.filter(pk=request.POST['class_id'])[0].anchor
				u.verb = GetNode('V/Flags/Class/Approved')
				u.save()

		if request.POST.has_key('anntext'):
			#	Send them to the create-miniblog form.
			return create_miniblog(request,'Web')

	has_ann_perms = UserBit.UserHasPerms(request.user, GetNode('Q/Web'), GetNode('V/Administer/Edit/Use'))
	if has_ann_perms:
		block_ann['sections'].append({'header' : 'General Announcements Control',
								'items' : [['<b>Careful</b>: announcements created here are seen by all.', None, '']],
								'input_items' : [['Add Announcement', 'anntext', 'Create...', '']]})
						
	programs_current = UserBit.find_by_anchor_perms(Program, curUser, GetNode('V/Administer/Edit'))
	
	approval_sections = []
	approval_headers = []
	program_classes = []
	
	proposed_classes = UserBit.find_by_anchor_perms(Class, curUser, GetNode('V/Flags/Class/Proposed'))

	for i in range(len(programs_current)):
		duplicate_flag = False
		p = programs_current[i]
		for j in range(1, i):
			if (p.id == programs_current[j].id):
				duplicate_flag = True
		program_classes = []
		if not duplicate_flag:
			for c in proposed_classes:
				if UserBit.UserHasPerms(curUser, c.anchor, GetNode('V/Flags/Class/Proposed')):
					program_classes.append([str(c), '/learn/' + c.url() + '/index.html',
						'<input class="button" type="submit" value="Approve"> / <input class="button" type="submit" value="Reject">'])
			approval_sections.append({'header' : str(p), 'items' : program_classes})
						
	block_approve = {	'title' : 'Approve Classes',
						'headers' : None,
						'sections' : approval_sections }
						
	blocks = [block_ann, block_approve]
	welcome_msg = 'This is your ESP "battle screen."  Have fun and don\'t break anything.'
					
	return render_to_response('battlescreens/general', {'request': request,
							   'blocks': blocks,
							   'page_title': 'MyESP: Administrator Home Page',
							   'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/')),
							   'welcome_msg': welcome_msg, 
							   'logged_in': request.user.is_authenticated() })

myesp_handlers = { 'register': myesp_register,
		   'finish': myesp_finish,
		   'emaillist': myesp_emaillist,
		   'emailfin': myesp_emailfin,
		   'signout': myesp_signout,
		   'login': myesp_login,
		   'logfin': myesp_logfin,
		   'home': myesp_home,
		   'student': myesp_battlescreen_student,
		   'teacher': myesp_battlescreen_teacher,
		   'admin': myesp_battlescreen_admin
		   }

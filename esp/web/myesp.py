from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.calendar.models import Event
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from esp.miniblog.views import preview_miniblog
from esp.program.models import Program, RegistrationProfile, Class, ClassCategories
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
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

	return render_to_response('users/newuser', {'request': request,
						    'Problem': False,
						    'logged_in': request.user.is_authenticated(),
						    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
						    'preload_images': preload_images})

def myesp_finish(request, module):
	""" Complete a user registration """
	for thing in ['confirm', 'password', 'username', 'email', "last_name", "first_name"]:
		if not request.POST.has_key(thing):
			return render_to_response('users/newuser', {'request': request,
								    'Problem': True,
								    'logged_in': request.user.is_authenticated(),
								    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
								    'preload_images': preload_images})

	if User.objects.filter(username=request.POST['username']).count() == 0:
			
		if request.POST['password'] != request.POST['confirm']:
			return render_to_response('users/newuser', {'request': request,
								    'Problem': True,
								   'logged_in': request.user.is_authenticated(),
								    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
								    'preload_images': preload_images})

		if len(User.objects.filter(email=request.POST['email'])) > 0:
			email_user = User.objects.filter(email=request.POST['email'])[0]
			email_user.username = request.POST['username']
			email_user.last_name = request.POST['last_name']
			email_user.first_name = request.POST['first_name']
			email_user.set_password(request.POST['password'])
			email_user.save()
			login(request, email_user)
			return render_to_response('users/regdone', {'request': request,
								    'logged_in': request.user.is_authenticated(),
								    'navbar_list': makeNavBar(request.user, GetNode('Q/Web/myesp/' + module)),
								    'preload_images': preload_images})							
		django_user = User()
		django_user.username = request.POST['username']
		django_user.last_name = request.POST['last_name']
		django_user.first_name = request.POST['first_name']
		django_user.set_password(request.POST['password'])
		django_user.email = request.POST['email']
		django_user.is_staff = False
		django_user.is_superuser = False
		django_user.save()
		login(request, django_user)
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
		return render_to_response('users/newuser', {'request': request,
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
		user = authenticate(username=request.POST['username'], password=request.POST['password'])
	else:
		user = None
	
	if user is not None:
		login(request, user)

	return myesp_logfin(request, module)

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
#	-	button label
#	-	button value (request.POST['action'] = value)

#	So a list item is a plain array of 3 containing
#	-	left-hand (wide) cell text 
#	-	left-hand (wide) cell url
#	-	right-hand (narrow) cell html including links but not formatting

#	That hopefully completes the array structure needed for this thing.

def myesp_battlescreen_student(request, module):
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	
	programs_current = UserBit.find_by_anchor_perms(Program, curUser, GetNode('V/Publish'));
	
	signup_sections = []
	
	for p in programs_current:
		signup_sections.append({'header' : str(p), 
								'items' : [['Information Page', '/learn/' + p.url() + '/index.html', ''],
										['Class Catalog', '/learn/' + p.url() + '/catalog/', ''],
										['Register for Classes', '/learn/' + p.url() + '/studentreg/', 'Help']]
								})
	
	block_ann = 	preview_miniblog(request)
				
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
							   'welcome_msg': welcome_msg,
							   'logged_in': request.user.is_authenticated() }) 

def myesp_battlescreen_teacher(request, module):
	curUser = request.user
	
	block_ann = preview_miniblog(request)
						
	blocks = [block_ann]
	welcome_msg = 'This is your ESP "battle screen," where you can sign up to teach, modify your class information, get in touch with your students, and review your history of interactions with ESP.'
						
	return render_to_response('battlescreens/general', {'request': request,
							   'blocks': blocks,
							   'welcome_msg': welcome_msg, 
							   'logged_in': request.user.is_authenticated() })
							   
def myesp_battlescreen_admin(request, module):
	curUser = request.user
	
	block_ann = preview_miniblog(request)
	
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
			#	Temporary anchor for now... I'm not sure where it should be
			qsc = GetNode('Q/ESP')
			has_perms = UserBit.UserHasPerms(request.user, qsc, GetNode('V/Post'))
			if has_perms:
				e = Entry()
				e.anchor = qsc
				e.title = request.POST['anntext']
				#	We don't necessarily want to make these one liners!
				e.content = e.title
				e.save()
	
	block_ann['sections'].append({'header' : 'Announcements Control',
								'items' : None,
								'input_items' : [['Add Announcement', 'anntext', 'Add', 'Announcement']]})
						
	programs_current = UserBit.find_by_anchor_perms(Program, curUser, GetNode('V/Administer/Program'))
	
	approval_sections = []
	approval_headers = []
	program_classes = []
	
	proposed_classes = UserBit.find_by_anchor_perms(Class, curUser, GetNode('V/Flags/Class/Proposed'))
	for p in programs_current:
		program_classes = []
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

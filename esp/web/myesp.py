from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.calendar.models import Event
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
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
#	-	footer text including links

#	The list item is displayed with a wide cell on the left followed by a narrow cell on the right.
#	The wide cell is like the name of some object to deal with,
#	and the narrow cell is like the administrative actions that can be applied to the object.
#	For example, the wide cell might have "Michael Price: Audio and Speakerbuilding" and the narrow cell
#	might be "Approve / Reject". 

#	So a list item is a plain array of size 2, containing
#	-	left-hand (wide) cell html including links but not formatting
#	-	right-hand (narrow) cell html including links but not formatting

#	That hopefully completes the array structure needed for this thing.

def myesp_battlescreen_student(request, module):
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	
	programs_current = UserBit.find_by_anchor_perms(Program, curUser, GetNode('V/Publish'));
	
	for p in programs_current:
		signup_sections.append({'header' : str(p), 
								'items' : [['<a href="' + p.url() + '">Information Page</a>', ''],
										['<a href="' + p.url() + '/catalog/">Class Catalog</a>', ''],
										['<a href="' + p.url() + '/studentreg/">Registration</a>', 'Help']]
								})
	
	block_ann = 	{	'title' : 'Announcements',
						'headers' : ann,
						'sections' : []
					}
				
	block_signup =  {	'title' : 'Register For ESP Programs',
						'headers' : ['Follow the links below to get started.'],
						'sections' : signup_sections
					}
					
	block_surveys = {	'title' : 'Online Surveys',
						'headers' : ['We\'re looking for your feedback so we can improve:'],
						'sections' : 
							[{	'header' : 'Splash Fall 2005',
								'items' : 	[['General Survey', ''],
											['Class 1 Survey', ''],
											['Class 2 Survey', '']]
							},
							{	'header' : 'Delve 2005 - 2006',
								'items' :	[['General Survey', '']]
							}]
					}
						
	blocks = [block_ann, block_signup, block_surveys]
	
	return render_to_response('battlescreens/general', {'request': request,
							   'blocks': blocks,
							   'logged_in': request.user.is_authenticated() }) 

def myesp_battlescreen_teacher(request, module):
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	
	block_ann = 	{	'title' : 'Announcements',
						'headers' : ['Announcement 1', 'Announcement 2', 'Announcement 3'],
						'sections' : None }
						
	blocks = [block_ann]
						
	return render_to_response('battlescreens/general', {'request': request,
							   'blocks': blocks,
							   'logged_in': request.user.is_authenticated() })
							   
def myesp_battlescreen_admin(request, module):
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	
	block_ann = 	{	'title' : 'Announcements',
						'headers' : ['Announcement 1', 'Announcement 2', 'Announcement 3'],
						'sections' : None }
						
	blocks = [block_ann]
					
	return render_to_response('battlescreens/general', {'request': request,
							   'blocks': blocks,
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

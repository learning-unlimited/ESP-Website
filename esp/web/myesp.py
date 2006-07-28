from django.contrib.auth import logout
from django.shortcuts import render_to_response
from esp.esp_local.navBar import makeNavBar
from django.shortcuts import render_to_response
from esp.calendar.models import Event
from esp.web.models import QuasiStaticData
from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from esp.program.models import RegistrationProfile, TimeSlot, Class, ClassCategories
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC
import datetime

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry

from esp.esp_local.data import navbar_data, preload_images


def myesp_register(request, module, user_id):
	if user_id: return render_to_response('users/duh', {'logged_in': True, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	return render_to_response('users/newuser', {'Problem': False,
		'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	

def myesp_finish(request, module, user_id):
	for thing in ['confirm', 'password', 'username', 'email', "last_name", "first_name"]:
		if not request.POST.has_key(thing):
			return render_to_response('users/newuser', {'Problem': True,
								  'logged_in': user_id, 'navbar_list': makeNavBar(request.path),
								    'preload_images': preload_images})
	if User.objects.filter(username=request.POST['username']).count() == 0:
			
		if request.POST['password'] != request.POST['confirm']:
			return render_to_response('users/newuser', {'Problem': True,
								   'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
		if len(User.objects.filter(email=request.POST['email'])) > 0:
			email_user = User.objects.filter(email=request.POST['email'])[0]
			email_user.username = request.POST['username']
			email_user.last_name = request.POST['last_name']
			email_user.first_name = request.POST['first_name']
			email_user.set_password(request.POST['password'])
			email_user.save()
			q = email_user.id
			request.session['user_id'] = q
			return render_to_response('users/regdone', {'logged_in': True, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})				
			
		django_user = User()
		django_user.username = request.POST['username']
		django_user.last_name = request.POST['last_name']
		django_user.first_name = request.POST['first_name']
		django_user.set_password(request.POST['password'])
		django_user.email = request.POST['email']
		django_user.is_staff = False
		django_user.is_superuser = False
		django_user.save()
		q = django_user.id
		request.session['user_id'] = q
		return render_to_response('users/regdone', {'logged_in': True, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})


def myesp_emaillist(request, module, user_id):
	return render_to_response('users/email', {'logged_in': False, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})

def myesp_emailfin(request, module, user_id):
	if not request.POST.has_key('email'):
		assert False, 1
		return render_to_response('users/newuser', {'Problem': True,
								    'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	if User.objects.filter(email=request.POST['email']).count() == 0:
		if User.objects.filter(email=request.POST['email']).count() > 0:
			return render_to_response('index.html', {
				'navbar_list': makeNavBar(request.path),
				'preload_images': preload_images,
				'logged_in': False})
			
		email_user = User()
		email_user.email = request.POST['email']
		email_user.username = request.POST['email']
		email_user.is_staff = False
		email_user.is_superuser = False
		email_user.save()
		return render_to_response('index.html', {
			'navbar_list': makeNavBar(request.path),
			'preload_images': preload_images,
			'logged_in': False})
	
def myesp_signout(request, module, user_id):
	logout(request)
	return render_to_response('users/logout', {'logged_in': False, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})


def myesp_login(request, module, user_id):
	q = request.session.get('user_id', None)
	if q is not None: render_to_response('users/duh', {'logged_in': True, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	return render_to_response('users/login', {'logged_in': False, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	
def myesp_logfin(request, module, user_id):
	for thing in ['password', 'username']:	
		if not request.POST.has_key(thing):
			return render_to_response('users/login', {'Problem': True,
									  'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	curUser = User.objects.filter(username=request.POST['username'])[0]
	if curUser.check_password(request.POST['password']):
		render_to_response('users/login', {'Problem': True,
							   'logged_in': False, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
		q = curUser.id
		request.session['user_id'] = q
		return render_to_response('index.html', {
			'navbar_list': makeNavBar(request.path),
			'preload_images': preload_images,
			'logged_in': True
			})
	else:
		return render_to_response('users/login', {'Problem': True, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})

def myesp_home(request, module, user_id):
	q = request.session.get('user_id', None)
	curUser = User.objects.filter(id=q)[0]
	sub = GetNode('V/Subscribe')
	ann = Entry.find_posts_by_perms(curUser, sub)
	ann = [x.html() for x in ann]
	return render_to_response('display/battlescreen', {'announcements': ann, 'logged_in': user_id})
						

myesp_handlers = { 'register': myesp_register,
		   'finish': myesp_finish,
		   'emaillist': myesp_emaillist,
		   'emailfin': myesp_emailfin,
		   'signout': myesp_signout,
		   'login': myesp_login,
		   'logfin': myesp_logfin,
		   'home': myesp_home
		   }

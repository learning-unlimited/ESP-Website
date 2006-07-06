from django.shortcuts import render_to_response
from esp.calendar.models import Event
from esp.web.models import QuasiStaticData
from django.http import HttpResponse, Http404

from django.contrib.auth.models import User

navbar_data = [
	{ 'link': '/teach/what-to-teach.html',
	  'text': 'What You Can Teach',
	'indent': False },
	{ 'link': '/teach/prev-classes.html',
	  'text': 'Previous Classes',
	  'indent': False },
	{ 'link': '/teach/teaching-time.html',
	  'text': 'Time Commitments',
	  'indent': False },
	{ 'link': '/teach/training.html',
	  'text': 'Teacher Training',
	  'indent': False },
	{ 'link': '/teach/ta.html',
	  'text': 'Become a TA',
	  'indent': False },
	{ 'link': '/teach/coteach.html',
	  'text': 'Co-Teach',
	  'indent': False },
	{ 'link': '/teach/reimburse.html',
	  'text': 'Reimbursements',
	  'indent': False },
	{ 'link': '/programs/hssp/teach.html',
	  'text': 'HSSP',
	  'indent': False },
	{ 'link': '/programs/hssp/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/teach/teacherinformation.html',
	  'text': 'Teacher Information',
	  'indent': True },
	{ 'link': '/programs/hssp/summerhssp.html',
	  'text': 'Summer HSSP',
	  'indent': False },
	{ 'link': '/programs/hssp/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/programs/firehose/teach.html',
	  'text': 'Firehose',
	  'indent': False },
	{ 'link': '/programs/junction/teach.html',
	  'text': 'JUNCTION',
	  'indent': False },
	{ 'link': '/programs/junction/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/programs/delve/teach.html',
	  'text': 'DELVE (AP Program)',
	  'indent': False }
]

preload_images = [
	'/media/images/level3/nav/home_ro.gif',
	'/media/images/level3/nav/discoveresp_ro.gif',
	'/media/images/level3/nav/takeaclass_ro.gif',
	'/media/images/level3/nav/volunteertoteach_ro.gif',
	'/media/images/level3/nav/getinvolved_ro.gif',
	'/media/images/level3/nav/archivesresources_ro.gif',
	'/media/images/level3/nav/myesp_ro.gif',
	'/media/images/level3/nav/contactinfo_ro.gif'
]
	  
def index(request):
	# Catherine: This does nothing
	latest_event_list = Event.objects.filter().order_by('-start')
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	return render_to_response('index.html', {
			'navbar_list': navbar_data,
			'preload_images': preload_images,
			'logged_in': user_id
		})

def myesp(request, module):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	if module == "register":
		return render_to_response('users/newuser', {'Problem': False,
			'logged_in': user_id})
	if module == "finish":
		for thing in ['confirm', 'password', 'username', 'email']:
			if not request.POST.has_key(thing):
				return render_to_response('users/newuser', {'Problem': True,
									  'logged_in': user_id})
		if User.objects.filter(username=request.POST['username']).count() == 0:
			
			if request.POST['password'] != request.POST['confirm']:
				render_to_response('users/newuser', {'Problem': True,
								   'logged_in': user_id})
			if User.objects.filter(email=request.POST['email']) > 0:
				email_user = User.objects.filter(email=request.POST['email'])[0]
				email_user.username = request.POST['username']
				email_user.set_password(request.POST['password'])
				email_user.save()
				q = email_user.id
				request.session['user_id'] = q
				return render_to_response('users/regdone', {'logged_in': True})				
			
			django_user = User()
			django_user.username = request.POST['username']
			django_user.set_password(request.POST['password'])
			django_user.email = request.POST['email']
			django_user.is_staff = False
			django_user.is_superuser = False
			django_user.save()
			q = django_user.id
			request.session['user_id'] = q
			return render_to_response('users/regdone', {'logged_in': True})
	if module == "emaillist":
		return render_to_response('users/email', {'logged_in': False})
	if module == "emailfin":
		if not request.POST.has_key('email'):
			assert False, 1
			return render_to_response('users/newuser', {'Problem': True,
								    'logged_in': user_id})
		if User.objects.filter(email=request.POST['email']).count() == 0:
			if User.objects.filter(email=request.POST['email']).count() > 0:
				return render_to_response('index.html', {
					'navbar_list': navbar_data,
					'preload_images': preload_images,
					'logged_in': False})
			
			email_user = User()
			email_user.email = request.POST['email']
			email_user.is_staff = False
			email_user.is_superuser = False
			email_user.save()
			return render_to_response('index.html', {
				'navbar_list': navbar_data,
				'preload_images': preload_images,
				'logged_in': False})
		
	if module == "signout":
		try: del request.session['user_id']
		except KeyError: pass
		return render_to_response('users/logout', {'logged_in': False})

	if module == "login":
		return render_to_response('users/login', {'logged_in': False})
	if module == "logfin":
		for thing in ['password', 'username']:
			if not request.POST.has_key(thing):
				return render_to_response('users/login', {'Problem': True,
									  'logged_in': user_id})
		curUser = User.objects.filter(username=request.POST['username'])[0]
		if curUser.check_password(request.POST['password']):
			render_to_response('users/login', {'Problem': True,
							   'logged_in': False})
			q = curUser.id
			request.session['user_id'] = q
			return render_to_response('index.html', {
				'navbar_list': navbar_data,
				'preload_images': preload_images,
				'logged_in': True
				})
		else:
			return render_to_response('users/login', {'Problem': True})
	return render_to_response('users/construction', {'logged_in': user_id})

def qsd(request, url):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url.split('/'))
	except QuasiStaticData.DoesNotExist:
		raise Http404
	return render_to_response('qsd.html', {
			'navbar_list': navbar_data,
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.html(),
			'logged_in': user_id})
	     

def qsd_raw(request, url):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url.split('/'))
	except QuasiStaticData.DoesNotExist:
		raise Http404
	return HttpResponse(qsd_rec.content, mimetype='text/plain')



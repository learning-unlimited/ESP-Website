from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.calendar.models import Event
from esp.qsd.models import QuasiStaticData
from esp.qsd.views import qsd, qsd_raw
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

from esp.web.data import navbar_data, preload_images
from esp.web.myesp import myesp_handlers
from esp.web.program import program_handlers

def index(request):
	""" Displays a generic "index" page """
	# Catherine: This does nothing
	# aseering: Yay.
	latest_event_list = Event.objects.filter().order_by('-start')
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	return render_to_response('index.html', {
		'navbar_list': navbar_data,
		'preload_images': preload_images,
		'logged_in': user_id
		})

def bio(request, tl, last, first):
	""" Displays a teacher bio """
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	user = User.objects.filter(last_name=last, first_name=first)
	if len(user) < 1: return render_to_response('users/construction', {'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images, 'tl': tl})
	bio = user[0].teacherbio_set.all()
	if len(bio) < 1: return render_to_response('users/construction', {'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images, 'tl': tl})
	bio = bio[0].html()
	return render_to_response('learn/bio', {'name': first + " " + last, 'bio': bio, 'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images, 'tl': tl})



def myesp(request, module):

	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
				
	if myesp_handlers.has_key(module):
		myesp_handlers[module](request, module, user_id)

	return render_to_response('users/construction', {'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})

def redirect(request, tl, one, three):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	Q_Prog = GetNode('Q/Programs')
	try:
		branch = Q_Prog.tree_decode(one.split("/"))
	except DataTree.NoSuchNodeException:
		return qsd(request, one + "/" +three+".html")

	qsd_rec = QuasiStaticData.objects.filter( path = branch, name = tl +  "-" + three )
	if len(qsd_rec) < 1:
		return qsd(request, one + "/" +three+".html")
	return render_to_response('qsd.html', {
		'navbar_list': makeNavBar(request.path),
		'preload_images': preload_images,
		'title': qsd_rec[0].title,
		'content': qsd_rec[0].html(),
		'logged_in': user_id})

def program(request, tl, one, two, module, extra = None):
	p = request.session.get('user_id', False)
	user_id = p
        if user_id != False: user_id = True

        curUser = User.objects.filter(id=p)[0]
	

        #if not user_id : return render_to_response('users/pleaselogin', {'logged_in': False, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
        #curUser = User.objects.filter(id=user_id)[0]

	treeItem = "Q/Programs/" + one + "/" + two 
	prog = GetNode(treeItem).program_set.all()
	if len(prog) < 1:
		return render_to_response('users/construction', {'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})
	prog = prog[0]

	if program_handlers.has_key(module):
		# aseering: Welcome to the deep, dark, magical world of lambda expressions!
		return program_handlers[module](request, tl, one, two, module, extra, user_id, p, curUser, prog)

	return render_to_response('users/construction', {'logged_in': user_id, 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})


def contact(request):
	return render_to_response('contact.html', { 'programs': UserBit.bits_get_qsc(AnonymousUser(), GetNode('V/Publish'), qsc_root=GetNode('Q/Programs')) })

def contact_submit(request):
	# I think we want to accept comments as long as they're submitted, regardless of what they contain. - aseering 7-20-2006
	for key in ['name', 'email', 'relation', 'publicity', 'program', 'comment']:
		if not request.POST.has_key(key):
			request.POST[key] = '(none)'
			#raise Http404

	t = loader.get_template('email/comment')

	m = MessageRequest()
	m.subject = 'User Comment: ' + request.POST['name']
	
	m.msgtext = t.render({
		'name': request.POST['name'],
		'email': request.POST['email'],
		'relation': request.POST['relation'],
		'publicity': request.POST['publicity'],
		'program': request.POST['program'],
		'comment': request.POST['comment'] })
	m.sender = request.POST['email']
	if not request.POST['program'] in GetNode('Q/Programs').children():
		m.category = GetNode('Q/ESP/Committees/Executive')
	else:
	        m.category = GetNode('Q/Programs/' + request.POST['program'])
		
	m.save()

	return qsd(request, 'contact/thanks')





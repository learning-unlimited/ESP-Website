from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.calendar.models import Event
from esp.qsd.models import QuasiStaticData
from esp.qsd.views import qsd, qsd_raw


from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from esp.program.models import RegistrationProfile, Class, ClassCategories
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
	return render_to_response('index.html', {
		'navbar_list': navbar_data,
		'preload_images': preload_images,
		'logged_in': request.user.is_authenticated()
		})

def bio(request, tl, last, first):
	""" Displays a teacher bio """
	bio = request.user.teacherbio_set.all()
	if len(bio) < 1: return render_to_response('users/construction', {'logged_in': request.user.is_authenticated(),
									  'navbar_list': makeNavBar(request.path),
									  'preload_images': preload_images,
									  'tl': tl})

	bio = bio[0].html()
	return render_to_response('learn/bio', {'name': first + " " + last,
						'bio': bio,
						'logged_in': request.user.is_authenticated(),
						'navbar_list': makeNavBar(request.path),
						'preload_images': preload_images,
						'tl': tl})



def myesp(request, module):
	""" Return page handled by myESP (generally, a user-specific page) """
	if myesp_handlers.has_key(module):
		return myesp_handlers[module](request, module)

	return render_to_response('users/construction', {'logged_in': request.user.is_authenticated(), 'navbar_list': makeNavBar(request.path), 'preload_images': preload_images})

#def redirect(request, tl, one, three):
#	Q_Prog = GetNode('Q/Programs')
#	try:
#		branch = Q_Prog.tree_decode(one.split("/"))
#	except DataTree.NoSuchNodeException:
#		return qsd(request, one + "/" +three+".html")
#
#	qsd_rec = QuasiStaticData.objects.filter( path = branch, name = tl +  "-" + three )
#	if len(qsd_rec) < 1:
#		return qsd(request, one + "/" +three+".html")
#
#	return render_to_response('qsd.html', {
#		'navbar_list': makeNavBar(request.path),
#		'preload_images': preload_images,
#		'title': qsd_rec[0].title,
#		'content': qsd_rec[0].html(),
#		'logged_in': request.user.is_authenticated() })

def redirect(request, url, section = 'Web', subsection = None):
	""" Universal mapping function between urls.py entries and QSD pages

	Calls esp.qsd.views.qsd to actually get the QSD pages; we just find them
	"""
	node = GetNode('Q/' + section)

	# URLs will be of the form "path/to/file.verb", or "path/to/file".
	# In the latter case, assume that verb = view
	# In either case, "path/to" is the tree path to the relevant page

	url_parts = url.split('/')
	url_address = url_parts.pop()

	url_address_parts = url_address.split('.')

	if len(url_address_parts) == 1: # We know the name; use the default verb
		qsd_name = url_address_parts[0]
		qsd_verb = 'view'
	elif len(url_address_parts) > 1: # We're given both pieces; hopefully that's all we're given (we're ignoring extra data here)
		qsd_name = url_address_parts[0]
		qsd_verb = url_address_parts[1]
	else: # In case someone breaks urls.py and "foo/.html" is allowed through
		qsd_name = 'index'
		qsd_verb = 'view'


	# If we have a subsection, descend into a node by that name
	if subsection == None:
		target_node = url
	else:
		target_node = url.append(subsection)

	# Get the node in question.  If it doesn't exist, deal with whether or not this user can create it.
	try:
		branch = node.tree_decode(target_node)
	except DataTree.NoSuchNodeException:
		# Check for permissions; if we have write bits here, create this node; otherwise return Http404
		return Http404

	
	

def program(request, tl, one, two, module, extra = None):
	""" Return program-specific pages """
	treeItem = "Q/Programs/" + one + "/" + two
	prog = GetNode(treeItem).program_set.all()
	if len(prog) < 1:
		return render_to_response('users/construction', {'logged_in': request.user.is_authenticated(),
								 'navbar_list': makeNavBar(request.path),
								 'preload_images': preload_images})

	prog = prog[0]

	if program_handlers.has_key(module):
		# aseering: Welcome to the deep, dark, magical world of lambda expressions!
		return program_handlers[module](request, tl, one, two, module, extra, prog)

	return render_to_response('users/construction', {'logged_in': request.user.is_authenticated(),
							 'navbar_list': makeNavBar(request.path),
							 'preload_images': preload_images})


def contact(request):
	return render_to_response('contact.html',
				  {'programs': UserBit.bits_get_qsc(AnonymousUser(),
								    GetNode('V/Publish'),
								    qsc_root=GetNode('Q/Programs')) })

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





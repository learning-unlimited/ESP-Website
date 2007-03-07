
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.cal.models import Event
from esp.qsd.models import QuasiStaticData
from esp.qsd.views import qsd

from esp.datatree.models import GetNode, DataTree
from esp.users.models import ContactInfo, UserBit, GetNodeOrNoBits, ESPUser
from esp.miniblog.models import Entry
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template import loader, Context
from icalendar import Calendar, Event as CalEvent, UTC

import datetime

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry
from esp.web.util.main import navbar_data, preload_images, render_to_response
from esp.web.views.myesp import myesp_handlers
from esp.web.views.program import program_handlers
from esp.web.views.archives import archive_handlers
from esp.miniblog.views import preview_miniblog
from esp.middleware import ESPError
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_control

@vary_on_headers('User-Agent')
def index(request):
	""" Displays a generic "index" page """
	# Catherine: This does nothing
	# aseering: Yay.
	# axiak:    hmm...
	announcements = preview_miniblog(request)

	backgrounds = ["/media/images/home/pagebkg1.jpg",
		       "/media/images/home/pagebkg2.jpg",
		       "/media/images/home/pagebkg3.jpg"]

	return render_to_response('index.html', request, None, {'announcements':    {'announcementList': announcements[:4],
										     'overflowed':       len(announcements) > 4,
										     'total':            len(announcements)},
								'backgrounds':      backgrounds})


@vary_on_headers('User-Agent')
@cache_control(private=True)
def myesp(request, module):
	""" Return page handled by myESP (generally, a user-specific page) """
	if myesp_handlers.has_key(module):
		return myesp_handlers[module](request, module)

	return render_to_response('users/construction', request, GetNode('Q/Web/myesp'), {})


@vary_on_headers('User-Agent')
def redirect(request, url, subsection = None, filename = "", section_redirect_keys = {}, section_prefix_keys = {}, renderer = qsd ):
	""" Universal mapping function between urls.py entries and QSD pages

	Calls esp.qsd.views.qsd to actually get the QSD pages; we just find them
	"""




	if filename != "":
		url = url + "/" + filename

	tree_branch = section_redirect_keys[subsection]

	# URLs will be of the form "path/to/file.verb", or "path/to/file".
	# In the latter case, assume that verb = view
	# In either case, "path/to" is the tree path to the relevant page

	url_parts = url.split('/')
	url_address = url_parts.pop()

	url_address_parts = url_address.split('.')

	if len(url_address_parts) == 1: # We know the name; use the default verb
		qsd_name = url_address_parts[0]

		qsd_verb = 'read'
	elif len(url_address_parts) == 2: # We're given both pieces; hopefully that's all we're given (we're ignoring extra data here)
		qsd_name = url_address_parts[0]
		qsd_verb = url_address_parts[1]
	else: # In case someone breaks urls.py and "foo/.html" is allowed through
		raise Http404

	# If we have a subsection, descend into a node by that name
	target_node = url_parts

	# Get the node in question.  If it doesn't exist, deal with whether or not this user can create it.
	try:
		branch_name = 'Q/' + tree_branch
		if target_node:
			branch_name = branch_name + '/' + "/".join(target_node)
		branch = GetNodeOrNoBits(branch_name, user=request.user)
	except DataTree.NoSuchNodeException:
		raise ESPError(False), "The requested directory does not exist."
		
	if url_parts:
		root_url = "/" + "/".join(url_parts) + "/" + qsd_name
	else:
		root_url = "/" + qsd_name


	section = ''
	if subsection == None:
		subsection_str = ''
	else:
		subsection_str = subsection + "/"
		root_url = "/" + subsection + root_url
		if section_prefix_keys.has_key(subsection):
			section = section_prefix_keys[subsection]
			qsd_name = section + ':' + qsd_name

	return renderer(request, branch, section, qsd_name, qsd_verb, root_url)
	
@vary_on_headers('User-Agent')
@cache_control(private=True)
def program(request, tl, one, two, module, extra = None):
	""" Return program-specific pages """

	#rom esp.dbmail.models import MessageRequest

	#oo = MessageRequest.objects.filter(processed = False)
	# = str(foo[0])
	
	#from django.http import HttpResponse
	
	#foo = 'Q/Programs/HSSP/2007_Test/Templates/Classrooms/26-332'
	#foo = GetNode(foo)
	#foo.save()
	#from esp.program.models import Program
	#hssp = Program.objects.filter(id=7)[0]
	#newhssp_anchor = hssp.anchor.parent.tree_create(['2007_Test'])
	#hssp.anchor.tree_create(['Classes']).rcopy(newhssp_anchor)
	
	#newhssp_anchor.tree_create(['foobar'])
	
	#return HttpResponse('Foo')
	#raise ESPError(), 'done'
	
	treeItem = "Q/Programs/" + one + "/" + two
	try:
		prog_tree = GetNode("Q/Programs")
		prog = prog_tree[one][two]
	except:
		raise ESPError(False), "Program not found."

	prog = prog.program_set.all()
	if len(prog) < 1:
		return render_to_response('errors/404.html', request, GetNode('Q/Web'), {})

	prog = prog[0]

	if program_handlers.has_key(module):
		# aseering: Welcome to the deep, dark, magical world of lambda expressions!
		return program_handlers[module](request, tl, one, two, module, extra, prog)

	from esp.program.modules.base import ProgramModuleObj
	newResponse = ProgramModuleObj.findModule(request, tl, one, two, module, extra, prog)

	if newResponse:
		return newResponse
	
	return render_to_response('errors/404.html', request, GetNode('Q/Web'), {})

def archives(request, selection, category = None, options = None):
	""" Return a page with class archives """
	
	sortparams = []
	if request.POST and request.POST.has_key('newparam'):
		if request.POST['newparam']:
			sortparams.append(request.POST['newparam'])
		for key in request.POST:
			if key.startswith('sortparam') and request.POST[key] != request.POST['newparam']: sortparams.append(request.POST[key])
	#	The selection variable is the type of data they want to see:
	#	classes, programs, teachers, etc.
	if archive_handlers.has_key(selection):
		return archive_handlers[selection](request, category, options, sortparams)
	
	return render_to_response('users/construction', request, GetNode('Q/Web'), {})
def contact(request):
	return render_to_response('contact.html', request, GetNode('Q/Web'),{'programs': UserBit.bits_get_qsc(AnonymousUser(),
								    GetNode('V/Publish'),
								    qsc_root=GetNode('Q/Programs')) })

def contact_submit(request):
	# I think we want to accept comments as long as they're submitted, regardless of what they contain. - aseering 7-20-2006
	for key in ['name', 'email', 'relation', 'publicity', 'program', 'comment']:
		if not request.POST.has_key(key):
			request.POST[key] = '(none)'

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

	return HttpResponseRedirect("/contact/thanks.html")






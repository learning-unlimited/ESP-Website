from esp.web.models import NavBarEntry
from esp.users.models import UserBit
from esp.datatree.models import GetNode
from django.http import HttpResponseRedirect, Http404
from esp.datatree.models import DataTree
from esp.dblog.models import error
from esp.dblog.views import ESPError

def makeNavBar(user, node, section = ''):
	""" Query the navbar-entry table for all navbar entries associated with this tree node """
	qsdTree = NavBarEntry.objects.filter(path__rangestart__lte=node.rangestart,path__rangeend__gte=node.rangeend,section=section).order_by('sort_rank')
	context = { 'node': node,
		 'has_edit_bits': UserBit.UserHasPerms(user, node, GetNode('V/Administer/Edit/QSD')),
		 'qsdTree': [ {'entry': x, 'has_bits': UserBit.UserHasPerms(user, x.path, GetNode('V/Administer/Edit/QSD')) } for x in qsdTree ],
		 'section': section }
	return context



def updateNavBar(request, section = ''): 
	""" Update a NavBar entry with the specified data """

	for i in [ 'navbar_id', 'action', 'new_url', 'node_id' ]:
		# Info can come by way of GET or POST, so we're using REQUEST
		# Could trusting GET be a problem?; I'm assuming Django
		# sessions are still maintained properly, so I can do security that way
		if not request.REQUEST.has_key(i):
			#raise Http404
			assert False, "Need " + str(i)

	action = request.REQUEST['action']

	try:
		if request.REQUEST['node_id'] == '':
			node = None
		else:
			node = DataTree.objects.filter(pk=request.REQUEST['node_id'])[0]
	except Exception:
		# raise Http404
		raise

	try:
		if request.REQUEST['navbar_id'] == '':
			navbar = None
		else:
			navbar = NavBarEntry.objects.filter(pk=request.REQUEST['navbar_id'])[0]
	except Exception:
		#raise Http404
		raise

	if not actions.has_key(request.REQUEST['action']):
		#raise Http404
		assert False, "Need action"

	if request.REQUEST.has_key('section'):
		section = request.REQUEST['section']

	actions[action](request, navbar, node, section)

	return HttpResponseRedirect(request.REQUEST['new_url'])

def navBarUp(request, navbar, node, section):
	""" Swap the sort_rank of the specified NavBarEntry and the NavBarEntry immediately before it in the list of NavBarEntrys associated with this tree node, so that this NavBarEntry appears to move up one unit on the page

	Fail silently if this is not possible
	"""
	if not UserBit.UserHasPerms(request.user, navbar.path, GetNode("V/Administer/Edit/QSD")):
		assert False, "You don't have permisssion to do that!"

	navbarList = NavBarEntry.objects.filter(path=navbar.path).order_by('sort_rank')

	if not navbar.indent:
		navbarList = navbarList.filter(indent=False)

	last_n = None

	for n in navbarList:
		if navbar == n and last_n != None:
			temp_sort_rank = n.sort_rank
			n.sort_rank = last_n.sort_rank
			last_n.sort_rank = temp_sort_rank

			n.save()
			last_n.save()

		last_n = n
		
	
def navBarDown(request, navbar, node, section):
	""" Swap the sort_rank of the specified NavBarEntry and the NavBarEntry immediately after it in the list of NavBarEntrys associated with this tree node, so that this NavBarEntry appears to move down one unit on the page

	Fail silently if this is not possible
	"""
	if not UserBit.UserHasPerms(request.user, navbar.path, GetNode("V/Administer/Edit/QSD")):
		assert False, "You don't have permisssion to do that!"

	navbarList = NavBarEntry.objects.filter(path=navbar.path).order_by('sort_rank')

	if not navbar.indent:
		navbarList = navbarList.filter(indent=False)

	last_n = None

	for n in navbarList:
		if last_n != None and navbar == last_n:
			temp_sort_rank = n.sort_rank
			n.sort_rank = last_n.sort_rank
			last_n.sort_rank = temp_sort_rank

			n.save()
			last_n.save()

		last_n = n
		

def navBarNew(request, navbar, node, section):
	""" Create a new NavBarEntry.  Put it at the bottom of the current sort_rank. """
	if not UserBit.UserHasPerms(request.user, node, GetNode("V/Administer/Edit/QSD")):
		assert False, "You don't have permisssion to do that!"

	try:
		max_sort_rank = NavBarEntry.objects.filter(path=node).order_by('-sort_rank')[0].sort_rank
	except IndexError:
		max_sort_rank = -100

	new_sort_rank = max_sort_rank + 100

	try:
		url = request.POST['url']

		entry = NavBarEntry()
		entry.path = node
		entry.sort_rank = new_sort_rank
		entry.link = url
		entry.text = request.POST['text']
		entry.indent = request.POST['indent']
		entry.section = section

		entry.save()
		
	except Exception:
		raise

	
def navBarDelete(request, navbar, node, section):
	if not UserBit.UserHasPerms(request.user, navbar.path, GetNode("V/Administer/Edit/QSD")):
		assert False, "You don't have permisssion to do that!"

	error("NavBar Delete logged", "We're disallowing NavBar deletes because we don't trust them")
	#navbar.delete()


actions = { 'up': navBarUp,
	    'down': navBarDown,
	    'new': navBarNew,
	    'delete': navBarDelete }


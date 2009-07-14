
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

from datetime import datetime

from django.contrib.auth.models import User, AnonymousUser
from django.db.models.query import Q

from esp.miniblog.views.blogs import *
from esp.miniblog.models import Entry, AnnouncementLink

from esp.cache import cache_function
from esp.web.util import render_to_response
from esp.datatree.models import *
from esp.users.models import UserBit, ESPUser
from esp.dbmail.models import MessageRequest, EmailRequest

def show_miniblog(request, url, subsection = None, section_redirect_keys = {}, extramsg=''):
    """ Shows a miniblog based on the specified node """
    user = request.user

    if subsection == None:
        tree_branch = 'Web'
    else:
        tree_branch = section_redirect_keys[subsection]

    node = 'Q/' + tree_branch + '/' + str(url)
    qsc = GetNode(node)

    entries = Entry.find_posts_by_perms(user, GetNode('V/Subscribe'), qsc=qsc)

    return render_to_response('miniblog.html', request, GetNode('Q/Web'), {'entries': entries,
                                                 'canpost': UserBit.UserHasPerms(user, qsc, GetNode('V/Administer/Edit/Use')),
                                                 'webnode': str(url),
                                                 'extramsg': extramsg })

def show_miniblog_entry(request, url, extramsg=''):
    """ Shows a miniblog based on the specified id """
    user = request.user
    entries = Entry.objects.filter(pk=int(url))

    # Assert permissions
    verb = GetNode( 'V/Subscribe' )
    for e in entries:
	    branch = e.anchor
	    if not UserBit.UserHasPerms( user, branch, verb ): assert False, "Insufficient permissions to view record"

    return render_to_response('miniblog.html', request, GetNode('Q/Web'), {'entries': entries,
												 'canpost': False,
                                                 'webnode': str(url),
                                                 'extramsg': extramsg })


def create_miniblog(request, url, tree_prefix = ''):
	user = request.user
	qsc = GetNode('Q/' + tree_prefix + str(url))

	has_perms = UserBit.UserHasPerms(user, qsc, GetNode('V/Administer/Edit/Use'))

	if has_perms:
		initial_title = ''
		if (request.POST and request.POST.has_key('anntext')):
			initial_title = request.POST['anntext']
		create_form_block = {'action': '/blog/' + url + '/post/',
							'title': 'Create Announcement: ' + initial_title,
							'headers': ['Announcement Details'],
							'lineitems': [{'label': 'Announcement Title', 'variable': 'title', 'default': initial_title}],
							'textboxes': [{'label': 'Announcement Content', 'variable': 'content', 'default': ''}]
							}
		return render_to_response('battlescreens/editor', request, GetNode('Q/Web'), {'blocks': [create_form_block]})
	else:
		assert False, 'Blog post failed.'

def post_miniblog(request, url, tree_prefix = ''):
    """ Add a post to a miniblog, then re-render the miniblog """
    for thing in ['title', 'content']:
        if not request.POST.has_key(thing):
            return show_miniblog(request, url, extramsg='Error: Failed post.  Please contact the server administrators.')

    user = request.user

    qsc = GetNode('Q/' + tree_prefix + str(url))

    has_perms = UserBit.UserHasPerms(user, qsc, GetNode('V/Administer/Edit/Use'))

    if has_perms:
        e = Entry()
        e.anchor = GetNode('Q/' + str(url))
        e.timestamp = datetime.now()
        e.title = request.POST['title']
        e.content = request.POST['content']
        e.save()
    else:
        return show_miniblog(request, '/blog/' + str(e.id) + '/', extramsg='Error: You don\'t have permission to post to this page.')

    return show_miniblog(request, '/blog/' + str(e.id) + '/')


#	Function for previewing announcements  - Michael P
#	Generates the block structure used by battle screens

def preview_miniblog(request, section = None):
    """this function will return the last n miniblog entries from preview_miniblog """
    # last update: Axiak

    if request.user != None:
        curUser = ESPUser(request.user)

    else:
        curUser = ESPUser(AnonymousUser())


    return curUser.getMiniBlogEntries()

@cache_function
def get_visible_announcements(user, limit):
    verb = GetNode('V/Subscribe')

    models_to_search = [Entry, AnnouncementLink]
    results = []
    grand_total = 0
    overflowed = False
    for model in models_to_search:
        result = UserBit.find_by_anchor_perms(model, user, verb).order_by('-timestamp').filter(Q(highlight_expire__gte = datetime.now()) | Q(highlight_expire__isnull = True))

        if limit:
            overflowed = ((len(result) - limit) > 0)
            total = len(result)
            result = result[:limit]
        else:
            overflowed = False
            total = len(result)

        results += result
        grand_total += total

    return {'announcementList': results,
              'overflowed':       overflowed,
              'total':            grand_total}
get_visible_announcements.depend_on_model(Entry)
get_visible_announcements.depend_on_model(AnnouncementLink)
# FIXME: Really should depend on the UserBit...

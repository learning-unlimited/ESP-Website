from django.shortcuts import render_to_response
from esp.miniblog.models import Entry
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import GetNode
from esp.users.models import UserBit
from esp.dbmail.models import MessageRequest, EmailRequest
from esp.dbmail.controllers import EmailController
from datetime import datetime

def show_miniblog(request, url, tree_prefix='', extramsg=''):
    """ Shows a miniblog based on the specified node """
    user = request.user

    node = 'Q/' + tree_prefix + str(url)
    qsc = GetNode(node)
        
    entries = Entry.find_posts_by_perms(user, GetNode('V/Subscribe'), qsc=qsc)

    return render_to_response('miniblog.html', { 'request': request,
                                                 'entries': entries,
                                                 'canpost': UserBit.UserHasPerms(user, qsc, GetNode('V/Post')),
                                                 'webnode': str(url),
                                                 'extramsg': extramsg })


def post_miniblog(request, url, tree_prefix=''):
    """ Add a post to a miniblog, then re-render the miniblog """
    for thing in ['title', 'content']:
        if not request.POST.has_key(thing):
            return show_miniblog(request, url, extramsg='Error: Failed post.  Please contact the server administrators.')

    user = request.user

    qsc = GetNode('Q/' + tree_prefix + str(url))

    has_perms = UserBit.UserHasPerms(user, qsc, GetNode('V/Post'))

    if has_perms:
        e = Entry()
        e.anchor = GetNode('Q/' + str(url))
        e.timestamp = datetime.now()
        e.title = request.POST['title']
        e.content = request.POST['content']
        e.save()

        # Also generate mail
        m = MessageRequest()
        m.subject = "Miniblog Update: " + e.title
        m.msgtext = e.content
        m.category = e.anchor
        m.sender = "ESP Miniblog E-mail System <esp@mit.edu>"
        m.save()

        EmailController().run()
    else:
        return show_miniblog(request, url, extramsg='Error: You don\'t have permission to post to this page.')

    return show_miniblog(request, url)


#	Function for previewing announcements  - Michael P
#	Generates the block structure used by battle screens
def preview_miniblog(request):
	curUser = request.user
	sub = GetNode('V/Subscribe')
	ann_posts = Entry.find_posts_by_perms(curUser, sub)
	ann_posts.sort(key=lambda obj:obj.timestamp)
	
	ann_items = []
	
	if ann_posts:
		#	Show only the 5 [or whatever] most recent announcements
		max_announcements = 5;
		if (len(ann_posts) < max_announcements):
			max_announcements = len(ann_posts)
		
		for i in range(len(ann_posts) - max_announcements - 1, len(ann_posts) - 1):
			x = ann_posts[i]
			ann_items.append(['<a href="/blog/' + str(x.anchor)[2:] + '">' + x.title + '</a>', None, '']);
			
		#	I've put a link in here to an all-announcements page that I didn't make yet.  Hold tight.
		if len(ann_posts) > 5:
			ann_items.append(['<b>' + str(len(ann_posts)) + ' total... </b><a href="/blog/announcements">see all</a>', None, ''])
	else:
		ann_items = [['No current announcements', None, '']]
	
	block_ann = 	{	'title' : 'Your Announcements',
						'headers' : None,
						'sections' : [{	'header': 'Recent Announcements',
										'items': ann_items}]}
	
	return block_ann

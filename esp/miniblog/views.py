from django.shortcuts import render_to_response
from esp.miniblog.models import Entry
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import GetNode
from esp.users.models import UserBit
from datetime import datetime

def show_miniblog(request, url, extramsg=''):
    """ Shows a miniblog based on the specified node """
    user = request.user

    node = 'Q/' + str(url)
    qsc = GetNode(node)
        
    entries = Entry.find_posts_by_perms(user, GetNode('V/Subscribe'), qsc=qsc)

    return render_to_response('miniblog.html', { 'entries': entries,
                                                 'canpost': UserBit.UserHasPerms(user, qsc, GetNode('V/Post')),
                                                 'webnode': str(url),
                                                 'extramsg': extramsg })


def post_miniblog(request, url):
    """ Add a post to a miniblog, then re-render the miniblog """
    for thing in ['title', 'content']:
        if not request.POST.has_key(thing):
            return show_miniblog(request, url, extramsg='Error: Failed post.  Please contact the server administrators.')

    user = request.user

    qsc = GetNode('Q/' + str(url))

    has_perms = UserBit.UserHasPerms(user, qsc, GetNode('V/Post'))

    if has_perms:
        e = Entry()
        e.anchor = GetNode('Q/' + str(url))
        e.timestamp = datetime.now()
        e.title = request.POST['title']
        e.content = request.POST['content']
        e.save()
    else:
        return show_miniblog(request, url, extramsg='Error: You don\'t have permission to post to this page.')

    return show_miniblog(request, url)

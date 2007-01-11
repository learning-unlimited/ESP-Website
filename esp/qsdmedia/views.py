from esp.qsdmedia.models import Media
from django.http import HttpResponseRedirect, Http404
from esp.users.models import UserBit
from esp.datatree.models import GetNode


def qsdmedia(request, branch, section, url_name, url_verb, base_url):
    """ Return a redirect to a media file """
    filename = url_name + '.' + url_verb

    if filename[:6] == 'learn:' or filename[:6] == 'teach:':
        filename = filename[6:]

    try:
        media_rec = Media.objects.get(anchor=branch, friendly_name=filename)
    except Media.DoesNotExist:
        raise Http404
    
    # aseering 8-7-2006: Add permissions enforcement; Only show the page if the current user has V/Flags/Public on this node
    have_view = UserBit.UserHasPerms( request.user, media_rec.anchor, GetNode('V/Flags/Public') )
    if have_view:
        return HttpResponseRedirect(media_rec.get_target_file_url())
    else:
        raise Http404

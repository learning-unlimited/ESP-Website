
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
from esp.qsdmedia.models import Media
from django.http import HttpResponseRedirect, HttpResponse, Http404
from esp.users.models import UserBit
from esp.datatree.models import *
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
import os.path

def qsdmedia(request, branch, section, url_name, url_verb, base_url):
    """ Return a redirect to a media file """
    filename = url_name + '.' + url_verb

    if filename[:6] == 'learn:' or filename[:6] == 'teach:':
        filename = filename[6:]

    try:
        media_rec = Media.objects.get(anchor=branch, friendly_name=filename)
    except Media.DoesNotExist:
        raise Http404
    except MultipleObjectsReturned: # If there exist multiple Media entries, we want the first one
        media_rec = Media.objects.filter(anchor=branch, friendly_name=filename).latest('id')

    
    # aseering 8-7-2006: Add permissions enforcement; Only show the page if the current user has V/Flags/Public on this node
    have_view = UserBit.UserHasPerms( request.user, media_rec.anchor, GetNode('V/Flags/Public') )
    if have_view:
        return HttpResponseRedirect(media_rec.target_file.url)
    else:
        raise Http404


def qsdmedia2(request, url):
    """ Download a media file """

    try:
        media_rec = Media.objects.get(hashed_name=url)
    except Media.DoesNotExist:
        raise Http404
    except MultipleObjectsReturned: # If there exist multiple Media entries, we want the first one
        media_rec = Media.objects.filter(hashed_name=url).latest('id')

    
    # aseering 8-7-2006: Add permissions enforcement; Only show the page if the current user has V/Flags/Public on this node
    have_view = request.user.isAdministrator() or UserBit.UserHasPerms( request.user, media_rec.anchor, GetNode('V/Flags/Public') )
    if have_view:
        file_name = os.path.join(settings.MEDIA_ROOT, "..", media_rec.target_file.url)
        f = open(file_name, 'rb')
        response = HttpResponse(f.read(), content_type=media_rec.mime_type)
        response['Content-Disposition'] = 'attachment; filename="' + media_rec.file_name + '"'
        return response
    else:
        raise Http404



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
    except AssertionError: # We get an AssertionError if 'get' fails because of multiple Media entries.  If there exist multiple Media entries, we want the first one
        media_rec = Media.objects.filter(anchor=branch, friendly_name=filename).order_by('-id')[0]

    
    # aseering 8-7-2006: Add permissions enforcement; Only show the page if the current user has V/Flags/Public on this node
    have_view = UserBit.UserHasPerms( request.user, media_rec.anchor, GetNode('V/Flags/Public') )
    if have_view:
        return HttpResponseRedirect(media_rec.target_file.url)
    else:
        raise Http404



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
  Email: web-team@learningu.org
"""
from esp.qsdmedia.models import Media
from django.http import HttpResponse, Http404
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
import fnmatch


def qsdmedia2(request, url, ignored_part=None):
    """ Download a media file """

    try:
        # the default format url=hashed_name/friendly_name
        #  the old format is url=hashed_name
        #  we only care about the part before the slash, if there is a slash
        #  so just look at url (since ignored_part is the second part if set)
        media_rec = Media.objects.get(hashed_name=url)
    except Media.DoesNotExist:
        # if the hashed name check failed, we may want to download based on the actual friendly filename
        try:
            media_rec = Media.objects.get(file_name=url)
        except Media.DoesNotExist:
            raise Http404
        except MultipleObjectsReturned:
            media_rec = Media.objects.filter(file_name=url).latest('id')
    except MultipleObjectsReturned: # If there exist multiple Media entries, we want the first one
        media_rec = Media.objects.filter(hashed_name=url).latest('id')

    file_name = media_rec.get_uploaded_filename()
    f = open(file_name, 'rb')
    response = HttpResponse(f.read(), content_type=media_rec.mime_type)

    inline_dispositions = ['application/pdf', 'image/*', 'audio/*', 'video/*']
    # these MIME types are served with Content-Disposition: inline (show in browser)
    # all others are served with Content-Disposition: attachment (download)
    disposition = 'attachment'
    for disp in inline_dispositions:
        if media_rec.mime_type and fnmatch.fnmatch(media_rec.mime_type, disp):
            disposition = 'inline'
            break
    response['Content-Disposition'] = disposition + '; filename="' + media_rec.file_name + '"'

    response['X-Content-Type-Options'] = 'nosniff'  # prevent browsers from second-guessing our MIME type
    return response


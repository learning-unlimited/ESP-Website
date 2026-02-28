
from io import open
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
from esp.utils.web import render_to_response
from esp.users.models import admin_required
from esp.web.forms.fileupload_form import FileUploadForm, FileRenameForm
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
import fnmatch


@admin_required
def site_media(request):
    """ Manage site-wide media (team photos, maps, policy docs) — not tied to a program. """
    uploadform = FileUploadForm()
    renameform = FileRenameForm()

    if request.method == 'POST':
        if request.POST.get('command') == 'delete':
            docid = request.POST.get('docid')
            try:
                media = Media.objects.get(id=docid, owner_type__isnull=True)
                media.delete()
            except Media.DoesNotExist:
                pass
            return HttpResponseRedirect('/manage/site_media/')
        if request.POST.get('command') == 'add':
            form = FileUploadForm(request.POST, request.FILES)
            if form.is_valid():
                media = Media(
                    friendly_name=form.cleaned_data['title'],
                    owner_type=None,
                    owner_id=None,
                )
                ufile = form.cleaned_data['uploadedfile']
                media.handle_file(ufile, ufile.name)
                media.format = ''
                media.save()
                return HttpResponseRedirect('/manage/site_media/')
            uploadform = form
        elif request.POST.get('command') == 'rename':
            form = FileRenameForm(request.POST, request.FILES)
            if form.is_valid():
                docid = request.POST.get('docid')
                try:
                    media = Media.objects.get(id=docid, owner_type__isnull=True)
                    media.rename(form.cleaned_data['title'])
                    media.save()
                    return HttpResponseRedirect('/manage/site_media/')
                except Media.DoesNotExist:
                    pass
            renameform = form

    site_media_list = Media.objects.filter(owner_type__isnull=True).order_by('friendly_name')
    context = {
        'site_media_list': site_media_list,
        'uploadform': uploadform,
        'renameform': renameform,
    }
    return render_to_response('qsdmedia/site_media.html', request, context)


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
    try:
        f = open(file_name, 'rb')
    except FileNotFoundError:
        raise Http404
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


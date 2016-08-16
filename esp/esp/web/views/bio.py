
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
from django.core.files.base import ContentFile

from esp.users.models     import ESPUser
from esp.program.models   import TeacherBio, Program, ArchiveClass
from esp.utils.web        import get_from_id, render_to_response
from django.http          import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.contrib.auth.decorators import login_required
from datetime             import datetime
from django.conf import settings

@login_required
def bio_edit(request, tl='', last='', first='', usernum=0, progid = None, username=''):
    """ Edits a teacher bio, given user and program identification information """

    old_url = False
    try:
        if tl == '':
            founduser = request.user
        else:
            if username != '':
                founduser = ESPUser.objects.get(username=username)
                old_url = (tl != 'teach')
            else:
                founduser = ESPUser.getUserFromNum(first, last, usernum)
                old_url = True
    except:
        return bio_not_found(request)

    foundprogram = get_from_id(progid, Program, 'program', False)

    return bio_edit_user_program(request, founduser, foundprogram,
                                 old_url=old_url)

@login_required
def bio_edit_user_program(request, founduser, foundprogram, external=False,
                          old_url=False):
    """ Edits a teacher bio, given user and program """

    if founduser is None or not founduser.isTeacher():
        return bio_not_found(request)

    if request.user.id != founduser.id and not request.user.isAdministrator():
        # To prevent querying whether a username exists, just return not found
        # here as well.
        return bio_not_found(request)

    lastbio      = TeacherBio.getLastBio(founduser)

    if old_url:
        # TODO(benkraft): after these URLs have been redirecting for a while,
        # remove them.
        return HttpResponsePermanentRedirect(lastbio.edit_url())

    # if we submitted a newly edited bio...
    from esp.web.forms.bioedit_form import BioEditForm
    if request.method == 'POST' and 'bio_submitted' in request.POST:
        form = BioEditForm(request.POST, request.FILES)

        if form.is_valid():
            if foundprogram is not None:
                # get the last bio for this program.
                progbio = TeacherBio.getLastForProgram(founduser, foundprogram)
            else:
                progbio = lastbio

            progbio.hidden = form.cleaned_data['hidden']
            # the slug bio and bio
            progbio.slugbio  = form.cleaned_data['slugbio']
            progbio.bio      = form.cleaned_data['bio']

            progbio.save()
            # save the image
            if form.cleaned_data['picture'] is not None:
                progbio.picture = form.cleaned_data['picture']
            else:
                progbio.picture = lastbio.picture
            progbio.save()
            if external:
                return True
            return HttpResponseRedirect(progbio.url())

    else:
        formdata = {'hidden': lastbio.hidden, 'slugbio': lastbio.slugbio,
                    'bio': lastbio.bio, 'picture': lastbio.picture}
        form = BioEditForm(formdata)

    return render_to_response('users/teacherbioedit.html', request, {'form':    form,
                                                   'institution': settings.INSTITUTION_NAME,
                                                   'user':    founduser,
                                                   'picture_file': lastbio.picture})



def bio_not_found(request, user=None, edit_url=None):
    response = render_to_response('users/teacherbionotfound.html', request,
                                  {'biouser': user,
                                   'edit_url': edit_url})
    response.status_code = 404
    return response

def bio(request, tl, last = '', first = '', usernum = 0, username = ''):
    """ Displays a teacher bio """

    try:
        if username != '':
            founduser = ESPUser.objects.get(username=username)
            old_url = (tl != 'teach')
        else:
            founduser = ESPUser.getUserFromNum(first, last, usernum)
            old_url = True
    except:
        return bio_not_found(request)

    return bio_user(request, founduser, old_url)

def bio_user(request, founduser, old_url=False):
    """ Display a teacher bio for a given user """

    if (not founduser or not founduser.is_active or not founduser.isTeacher()):
        return bio_not_found(request)

    teacherbio = TeacherBio.getLastBio(founduser)
    if teacherbio.hidden:
        return bio_not_found(request, founduser, teacherbio.edit_url())

    if old_url:
        # TODO(benkraft): after these URLs have been redirecting for a while,
        # remove them.
        return HttpResponsePermanentRedirect(teacherbio.url())

    if not teacherbio.picture:
        teacherbio.picture = 'images/not-available.jpg'

    if teacherbio.slugbio is None or len(teacherbio.slugbio.strip()) == 0:
        teacherbio.slugbio = 'ESP Teacher'
    if teacherbio.bio is None or len(teacherbio.bio.strip()) == 0:
        teacherbio.bio     = 'Not Available.'

    now = datetime.now()

    # Only show classes that were approved and that have already run
    # If we show classes that are yet to run, it's possible that
    # the corresponding course catalog isn't up yet, in which case
    # the teacher-bio pages leak information.
    # Also, sort by the order of the corresponding program's id.
    # This should roughly order by program date; at the least, it will
    # cluster listed classes by program.
    recent_classes = founduser.getTaughtClassesAll().filter(status__gte=10).exclude(meeting_times__end__gte=now).exclude(sections__meeting_times__end__gte=now).filter(sections__resourceassignment__resource__res_type__name="Classroom").distinct().order_by('-parent_program__id')

    # Ignore archived classes where we still have a log of the original class
    # Archives lose information; so, display the original form if we still have it
    cls_ids = [x.id for x in recent_classes]
    classes = ArchiveClass.getForUser(founduser).exclude(original_id__in=cls_ids)

    return render_to_response('users/teacherbio.html', request,
                              {'biouser': founduser,
                               'bio': teacherbio,
                               'classes': classes,
                               'recent_classes': recent_classes,
                               'institution': settings.INSTITUTION_NAME})


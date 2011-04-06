
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
from django.core.files.base import ContentFile

from esp.users.models     import ESPUser
from esp.program.models   import TeacherBio, Program, ArchiveClass
from esp.web.util         import get_from_id, render_to_response
from esp.datatree.models  import *
from django.http          import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from esp.middleware       import ESPError
from datetime             import datetime
from esp                  import settings

@login_required
def bio_edit(request, tl='', last='', first='', usernum=0, progid = None, external = False, username=''):
    """ Edits a teacher bio, given user and program identification information """
    
    try:
        if tl == '':
            founduser = ESPUser(request.user)
        else:
            if username != '':
                founduser = ESPUser.objects.get(username=username)
            else:
                founduser = ESPUser.getUserFromNum(first, last, usernum)
    except:
        raise Http404
    
    foundprogram = get_from_id(progid, Program, 'program', False)

    return bio_edit_user_program(request, founduser, foundprogram, external)

@login_required
def bio_edit_user_program(request, founduser, foundprogram, external=False):
    """ Edits a teacher bio, given user and program """

    if founduser is None:
        if external:
            raise ESPError(), 'No user given.'
        else:
            raise Http404

    if not founduser.isTeacher():
        raise ESPError(False), '%s is not a teacher of ESP.' % \
                               (founduser.name())

    if request.user.id != founduser.id and request.user.is_staff != True:
        raise ESPError(False), 'You are not authorized to edit this biography.'
        
    lastbio      = TeacherBio.getLastBio(founduser)
        
    
    # if we submitted a newly edited bio...
    from esp.web.forms.bioedit_form import BioEditForm
    if request.method == 'POST' and request.POST.has_key('bio_submitted'):
        form = BioEditForm(request.POST, request.FILES)

        if form.is_valid():
            if foundprogram is not None:
                # get the last bio for this program.
                progbio = TeacherBio.getLastForProgram(founduser, foundprogram)
            else:
                progbio = lastbio

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
        formdata = {'slugbio': lastbio.slugbio, 'bio': lastbio.bio, 'picture': lastbio.picture}
        form = BioEditForm(formdata)
        
    return render_to_response('users/teacherbioedit.html', request, GetNode('Q/Web/myesp'), {'form':    form,
                                                   'institution': settings.INSTITUTION_NAME,
                                                   'user':    founduser,
                                                   'picture_file': lastbio.picture})

    
    

def bio(request, tl, last = '', first = '', usernum = 0, username = ''):
    """ Displays a teacher bio """

    try:
        if username != '':
            founduser = ESPUser.objects.get(username=username)
        else:
            founduser = ESPUser.getUserFromNum(first, last, usernum)
    except:
        raise Http404

    return bio_user(request, founduser)

def bio_user(request, founduser):
    """ Display a teacher bio for a given user """
    
    if founduser is None:
        raise Http404

    if founduser.is_active == False:
        raise Http404

    if not founduser.isTeacher():
        raise ESPError(False), '%s is not a teacher of ESP.' % \
                               (founduser.name())
    
    teacherbio = TeacherBio.getLastBio(founduser)
    if not teacherbio.picture:
        teacherbio.picture = 'uploaded/not-available.jpg'
        
    if teacherbio.slugbio is None or len(teacherbio.slugbio.strip()) == 0:
        teacherbio.slugbio = 'ESP Teacher'
    if teacherbio.bio is None or len(teacherbio.bio.strip()) == 0:
        teacherbio.bio     = 'Not Available.'

    now = datetime.now()

    # Only show classes that were approved and that have already run
    # If we show classes that are yet to run, it's possible that
    # the corresponding course catalog isn't up yet, in which case
    # the teacher-bio pages leak information.
    # Also, sort by the order of the corresponding program's DataTree node.
    # This should roughly order by program date; at the least, it will
    # cluster listed classes by program.
    recent_classes = founduser.getTaughtClassesAll().filter(status__gte=10).exclude(meeting_times__end__gte=now).exclude(sections__meeting_times__end__gte=datetime.now()).filter(sections__resourceassignment__resource__res_type__name="Classroom").order_by('-anchor__parent__parent__id')

    # Ignore archived classes where we still have a log of the original class
    # Archives lose information; so, display the original form if we still have it
    cls_ids = [x.id for x in recent_classes]
    classes = ArchiveClass.getForUser(founduser).exclude(original_id__in=cls_ids)

    return render_to_response('users/teacherbio.html', request, GetNode('Q/Web/Bio'),
                              {'biouser': founduser,
                               'bio': teacherbio,
                               'classes': classes,
                               'recent_classes': recent_classes})


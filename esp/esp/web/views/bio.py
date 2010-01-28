
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
from django.core.files.base import ContentFile

from esp.users.models     import ESPUser
from esp.program.models   import TeacherBio, Program, ArchiveClass
from esp.web.util         import get_from_id, render_to_response
from esp.datatree.models  import *
from django.http          import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from esp.middleware       import ESPError

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
                try:
                    picture = form.cleaned_data['picture']
                    picture.seek(0)
                    progbio.picture.save(picture.name, ContentFile(picture.read()))
                except:
                    #   If you run into a problem processing the image, just ignore it.
                    progbio.picture = lastbio.picture
                    progbio.save()
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


    classes = ArchiveClass.getForUser(founduser)

    return render_to_response('users/teacherbio.html', request, GetNode('Q/Web/Bio'), {'biouser': founduser,
                                               'bio': teacherbio,
                                               'classes': classes})


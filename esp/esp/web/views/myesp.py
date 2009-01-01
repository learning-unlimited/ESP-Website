
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
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from esp.users.models import ContactInfo, UserBit, ESPUser, TeacherInfo, StudentInfo, EducatorInfo, GuardianInfo
from esp.datatree.models import *
from esp.miniblog.models import AnnouncementLink, Entry
from esp.miniblog.views import preview_miniblog
from esp.program.models import Program, RegistrationProfile, ClassSubject
from django.http import Http404, HttpResponseRedirect
import datetime
from esp.middleware import ESPError
from esp.users.forms.password_reset import UserPasswdForm
from esp.web.util.main import render_to_response
from django.db.models.query import Q

@login_required
def myesp_passwd(request, module):
        """ Change password """
        if request.user.username == 'onsite':
                raise ESPError(False), "Sorry, you're not allowed to change the password of this user. It's special."

        if request.method == "POST":
                form = UserPasswdForm(user=request.user, data=request.POST)
                if form.is_valid():
                        new_data = form.cleaned_data
                        user = authenticate(username=request.user.username,
                                            password=new_data['password'])
                        
                        user.set_password(new_data['newpasswd'])
                        user.save()
                        login(request, user)
                        return render_to_response('users/passwd.html', request, GetNode('Q/Web/myesp'), {'Success': True})
        else:
                form = UserPasswdForm(user=request.user)
                
        return render_to_response('users/passwd.html', request, GetNode('Q/Web/myesp'), {'Problem': False,
                                                    'form': form,
                                                    'Success': False})


def myesp_home(request, module):
	""" Draw the ESP home page """
	curUser = request.user
	sub = GetNode('V/Subscribe')
	entries = Entry.find_posts_by_perms(curUser, sub)
	annlinks = AnnouncementLink.find_posts_by_perms(curUser, sub)
	entries = [x.html() for x in entries.filter(Q(highlight_expire__isnull=True) | Q(highlight_expire__gte=datetime.datetime.now()))]
	annlinks = [x.html() for x in annlinks.filter(Q(highlight_expire__isnull=True) | Q(highlight_expire__gte=datetime.datetime.now()))]
	ann = entries + annlinks
	return render_to_response('display/battlescreen', request, GetNode('Q/Web/myesp'), {'announcements': ann})

@login_required
def myesp_switchback(request, module):
	user = request.user
	user = ESPUser(user)
	user.updateOnsite(request)

	if not user.other_user:
		raise ESPError(False), 'You were not another user!'

	return HttpResponseRedirect(user.switch_back(request))

@login_required
def edit_profile(request, module):

    curUser = ESPUser(request.user)

    if curUser.isStudent():
        return profile_editor(request, None, True, 'student')

    elif curUser.isTeacher():
        return profile_editor(request, None, True, 'teacher')

    elif curUser.isGuardian():
        return profile_editor(request, None, True, 'guardian')

    elif curUser.isEducator():
        return profile_editor(request, None, True, 'educator')	

    else:
        user_types = UserBit.valid_objects().filter(verb__parent=GetNode("V/Flags/UserRole")).select_related().order_by('-id')
        return profile_editor(request, None, True, user_types[0].verb.name if user_types else '')

@login_required
def profile_editor(request, prog_input=None, responseuponCompletion = True, role=''):
    """ Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

    from esp.users.models import K12School
    from esp.web.views.main import registration_redirect
    
    STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRep')
    STUDREP_QSC  = GetNode('Q')


    if prog_input is None:
        prog = Program.objects.get(anchor = GetNode('Q/Programs/Dummy_Programs/Profile_Storage'))
        navnode = GetNode('Q/Web/myesp')
    else:
        prog = prog_input
        navnode = prog.anchor

    curUser = request.user
    context = {'logged_in': request.user.is_authenticated() }
    context['user'] = request.user

    curUser = ESPUser(curUser)
    curUser.updateOnsite(request)

    #   Get the profile form from the user's type, although we need to handle 
    #   a couple of extra possibilities for the 'role' variable.
    user_types = ESPUser.getAllUserTypes()
    additional_types = {'': {'label': 'Not specified', 'profile_form': 'UserContactForm'},
                        'Administrator': {'label': 'Administrator', 'profile_form': 'UserContactForm'},
                       }
    #   Handle all-lowercase versions of role being passed in by calling title()
    if role.title() in user_types:
        target_type = user_types[role.title()]
    else:
        target_type = additional_types[role.title()]
    mod = __import__('esp.users.forms.user_profile', (), (), target_type['profile_form'])
    FormClass = getattr(mod, target_type['profile_form'])

    context['profiletype'] = role

    if request.method == 'POST' and request.POST.has_key('profile_page'):
        form = FormClass(curUser, request.POST)

        # Don't suddenly demand an explanation from people who are already student reps
        if UserBit.objects.UserHasPerms(curUser, STUDREP_QSC, STUDREP_VERB):
            if hasattr(form, 'repress_studentrep_expl_error'):
                form.repress_studentrep_expl_error()

        if form.is_valid():
            new_data = form.cleaned_data

            regProf = RegistrationProfile.getLastForProgram(curUser, prog)

            if regProf.id is None:
                old_regProf = RegistrationProfile.getLastProfile(curUser)
            else:
                old_regProf = regProf

            for field_name in ['address_zip','address_city','address_street','address_state']:
                if new_data[field_name] != getattr(old_regProf.contact_user,field_name,False):
                    new_data['address_postal'] = ''

            if new_data['address_postal'] == '':
                new_data['address_postal'] = False

            regProf.contact_user = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_user, '', curUser)
            regProf.contact_emergency = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_emergency, 'emerg_')

            if new_data.has_key('dietary_restrictions') and new_data['dietary_restrictions']:
                regProf.dietary_restrictions = new_data['dietary_restrictions']

            if role == 'student':
                regProf.student_info = StudentInfo.addOrUpdate(curUser, regProf, new_data)
                regProf.contact_guardian = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_guardian, 'guard_')
            elif role == 'teacher':
                regProf.teacher_info = TeacherInfo.addOrUpdate(curUser, regProf, new_data)
            elif role == 'guardian':
                regProf.guardian_info = GuardianInfo.addOrUpdate(curUser, regProf, new_data)
            elif role == 'educator':
                regProf.educator_info = EducatorInfo.addOrUpdate(curUser, regProf, new_data)
            blah = regProf.__dict__
            regProf.save()

            curUser.first_name = new_data['first_name']
            curUser.last_name  = new_data['last_name']
            curUser.email     = new_data['e_mail']
            curUser.save()
            if responseuponCompletion == True:
                return registration_redirect(request)
            else:
                return True
        else:
            #   Force loading the school back in if possible...
            replacement_data = form.data.copy()
            try:
                replacement_data['k12school'] = form.fields['k12school'].clean(form.data['k12school']).id
            except:
                pass
            form = FormClass(curUser, replacement_data)

    else:
        if prog_input is None:
            regProf = RegistrationProfile.getLastProfile(curUser)
        else:
            regProf = RegistrationProfile.getLastForProgram(curUser, prog)
        if regProf.id is None:
            regProf = RegistrationProfile.getLastProfile(curUser)
        new_data = {}
        if curUser.isStudent():
            new_data['studentrep'] = (UserBit.objects.filter(user = curUser,
                                     verb = STUDREP_VERB,
                                     qsc  = STUDREP_QSC).count() > 0)
        new_data['first_name'] = curUser.first_name
        new_data['last_name']  = curUser.last_name
        new_data['e_mail']     = curUser.email
        new_data = regProf.updateForm(new_data, role)
        if request.session.has_key('birth_month') and request.session.has_key('birth_day'):
            new_data['dob'] = datetime.date(1994, int(request.session['birth_month']), int(request.session['birth_day']))
        if request.session.has_key('school_id'):
            new_data['k12school'] = request.session['school_id']

        #   Set default values for state fields
        state_fields = ['address_state', 'emerg_address_state']
        state_tag_map = {}
        for field in state_fields:
            state_tag_map[field] = 'local_state'
        form = FormClass(curUser, initial=new_data, tag_map=state_tag_map)

    context['request'] = request
    context['form'] = form
    return render_to_response('users/profile.html', request, navnode, context)

@login_required
def myesp_onsite(request, module):
	
	user = ESPUser(request.user)
	if not user.isOnsite():
		raise ESPError(False), 'You are not a valid on-site user, please go away.'
	verb = GetNode('V/Registration/OnSite')
	
	progs = UserBit.find_by_anchor_perms(Program, user = user, verb = verb)

        # Order them decreasing by id
        # - Currently reverse the list in Python, otherwise fbap's cache is ignored
        # TODO: Fix this
        progs = list(progs)
        progs.reverse()

	if len(progs) == 1:
		return HttpResponseRedirect('/onsite/%s/main' % progs[0].getUrlBase())
	else:
		navnode = GetNode('Q/Web/myesp')
		return render_to_response('program/pickonsite.html', request, navnode, {'progs': progs})

myesp_handlers = {
		   'home': myesp_home,
		   'switchback': myesp_switchback,
		   'onsite': myesp_onsite,
		   'passwd': myesp_passwd,
		   'profile': edit_profile
		   }


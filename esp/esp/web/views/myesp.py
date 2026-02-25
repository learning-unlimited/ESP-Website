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
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from esp.users.models import ContactInfo, ESPUser, TeacherInfo, StudentInfo, EducatorInfo, GuardianInfo, Permission
from esp.miniblog.models import AnnouncementLink, Entry
from esp.miniblog.views import preview_miniblog
from esp.program.models import Program, RegistrationProfile, ClassSubject
from esp.tagdict.models import Tag
from django.http import Http404, HttpResponseRedirect
import datetime
from esp.middleware import ESPError
from esp.users.forms.password_reset import UserPasswdForm
from esp.users.forms.user_profile import TeacherInfoForm, StudentInfoForm, EducatorInfoForm, GuardianInfoForm, EmergContactForm, GuardContactForm
from esp.utils.web import render_to_response
from django.db.models.query import Q

# Mapping from role name to (FormClass, takes_user_arg).
# takes_user_arg is True for forms inheriting from FormUnrestrictedOtherUser.
ROLE_INFO_FORMS = {
    'student': (StudentInfoForm, True),
    'teacher': (TeacherInfoForm, False),
    'guardian': (GuardianInfoForm, False),
    'educator': (EducatorInfoForm, False),
}

# Sub-forms for specific roles: list of (FormClass, takes_user_arg) tuples.
ROLE_EXTRA_SUBFORMS = {
    'student': [(GuardContactForm, True), (EmergContactForm, True)],
}

@login_required
def myesp_passwd(request):
        """ Change password """
        if request.user.username == 'onsite':
                raise ESPError("Sorry, you're not allowed to change the password of this user. It's special.", log=False)

        if request.method == "POST":
                form = UserPasswdForm(user=request.user, data=request.POST)
                if form.is_valid():
                        new_data = form.cleaned_data
                        user = authenticate(username=request.user.username,
                                            password=new_data['password'])

                        user.set_password(new_data['newpasswd'])
                        user.save()
                        login(request, user)
                        return render_to_response('users/passwd.html', request, {'Success': True})
        else:
                form = UserPasswdForm(user=request.user)

        return render_to_response('users/passwd.html', request, {'Problem': False,
                                                    'form': form,
                                                    'Success': False})

@login_required
def myesp_accountmanage(request):
    return render_to_response('users/account_manage.html', request, {})

@login_required
def myesp_switchback(request):
    user = request.user
    user.updateOnsite(request)

    if not user.other_user:
        raise ESPError('You were not another user!', log=False)

    return HttpResponseRedirect(user.switch_back(request))

@login_required
def edit_profile(request):

    curUser = request.user

    valid_types = [t.lower() for t in ESPUser.getTypes()]
    user_roles = [t.lower() for t in curUser.getUserTypes() if t.lower() in valid_types]

    if not user_roles:
        user_types = curUser.groups.all().order_by('-id')
        user_roles = [user_types[0].name.lower()] if user_types else ['']

    return profile_editor(request, None, True, user_roles)

@login_required
def profile_editor(request, prog_input=None, responseuponCompletion = True, role=''):
    """ Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

    from esp.users.models import K12School
    from esp.web.views.main import registration_redirect

    if prog_input is None:
        prog = None
    else:
        prog = prog_input

    curUser = request.user
    context = {'logged_in': request.user.is_authenticated }
    context['user'] = request.user
    context['program'] = prog

    curUser.updateOnsite(request)

    if isinstance(role, str):
        roles = [role]
    else:
        roles = list(role)

    primary_role = roles[0] if roles else ''
    extra_roles = roles[1:] if len(roles) > 1 else []

    #   Get the profile form from the user's type, although we need to handle
    #   a couple of extra possibilities for the 'role' variable.
    user_types = ESPUser.getAllUserTypes()
    additional_types = [['',  {'label': 'Not specified', 'profile_form': 'UserContactForm'}],
                        ['Administrator', {'label': 'Administrator', 'profile_form': 'UserContactForm'}],
                       ]
    additional_type_labels = [x[0] for x in additional_types]
    #   Handle all-lowercase versions of role being passed in by calling title()
    user_type_labels = [x[0] for x in user_types]
    if primary_role.title() in user_type_labels:
        target_type = user_types[user_type_labels.index(primary_role.title())][1]
    else:
        target_type = additional_types[additional_type_labels.index(primary_role.title())][1]
    mod = __import__('esp.users.forms.user_profile', (), (), target_type['profile_form'])
    FormClass = getattr(mod, target_type['profile_form'])

    context['profiletype'] = primary_role

    # Build list of extra info form classes for additional roles.
    extra_form_specs = []
    for extra_role in extra_roles:
        if extra_role in ROLE_INFO_FORMS:
            info_form_cls, takes_user = ROLE_INFO_FORMS[extra_role]
            prefix = extra_role + '_extra'
            extra_form_specs.append({
                'role': extra_role,
                'form_class': info_form_cls,
                'prefix': prefix,
                'takes_user': takes_user,
            })
            # Also add any sub-forms (e.g., guardian/emergency contacts for students)
            for sub_form_cls, sub_takes_user in ROLE_EXTRA_SUBFORMS.get(extra_role, []):
                sub_prefix = extra_role + '_' + sub_form_cls.__name__.lower()
                extra_form_specs.append({
                    'role': extra_role,
                    'form_class': sub_form_cls,
                    'prefix': sub_prefix,
                    'is_subform': True,
                    'takes_user': sub_takes_user,
                })
    extra_forms = []
    if request.method == 'POST' and 'profile_page' in request.POST:
        form = FormClass(curUser, request.POST)

        # Don't suddenly demand an explanation from people who are already student reps
        if curUser.hasRole("StudentRep"):
            if hasattr(form, 'repress_studentrep_expl_error'):
                form.repress_studentrep_expl_error()

        extra_forms = []
        for spec in extra_form_specs:
            if spec.get('takes_user', False):
                ef = spec['form_class'](curUser, request.POST, prefix=spec['prefix'])
            else:
                ef = spec['form_class'](request.POST, prefix=spec['prefix'])
            extra_forms.append({
                'form': ef,
                'role': spec['role'],
                'prefix': spec['prefix'],
                'is_subform': spec.get('is_subform', False),
            })

        # Check if all forms are valid
        all_extra_valid = all(ef['form'].is_valid() for ef in extra_forms)

        if form.is_valid() and all_extra_valid:
            new_data = form.cleaned_data

            if prog_input is None:
                regProf = RegistrationProfile.getLastProfile(curUser)
            else:
                regProf = RegistrationProfile.getLastForProgram(curUser, prog)

            if regProf.id is None:
                old_regProf = RegistrationProfile.getLastProfile(curUser)
            else:
                old_regProf = regProf

            regProf.contact_user = ContactInfo.addOrUpdate(curUser, regProf, new_data, regProf.contact_user, '')

            if new_data.get('dietary_restrictions'):
                regProf.dietary_restrictions = new_data['dietary_restrictions']

            if primary_role == 'student':
                regProf.student_info = StudentInfo.addOrUpdate(curUser, regProf, new_data)
                regProf.contact_guardian = ContactInfo.addOrUpdate(curUser, regProf, new_data, regProf.contact_guardian, 'guard_')
                regProf.contact_emergency = ContactInfo.addOrUpdate(curUser, regProf, new_data, regProf.contact_emergency, 'emerg_')
            elif primary_role == 'teacher':
                regProf.teacher_info = TeacherInfo.addOrUpdate(curUser, regProf, new_data)
            elif primary_role == 'guardian':
                regProf.guardian_info = GuardianInfo.addOrUpdate(curUser, regProf, new_data)
            elif primary_role == 'educator':
                regProf.educator_info = EducatorInfo.addOrUpdate(curUser, regProf, new_data)

            # Save extra role info
            for ef in extra_forms:
                if ef['is_subform']:
                    continue
                extra_data = ef['form'].cleaned_data
                extra_role_name = ef['role']
                if extra_role_name == 'student':
                    regProf.student_info = StudentInfo.addOrUpdate(curUser, regProf, extra_data)
                elif extra_role_name == 'teacher':
                    regProf.teacher_info = TeacherInfo.addOrUpdate(curUser, regProf, extra_data)
                elif extra_role_name == 'guardian':
                    regProf.guardian_info = GuardianInfo.addOrUpdate(curUser, regProf, extra_data)
                elif extra_role_name == 'educator':
                    regProf.educator_info = EducatorInfo.addOrUpdate(curUser, regProf, extra_data)

            for ef in extra_forms:
                if ef['is_subform'] and ef['role'] == 'student':
                    sub_data = ef['form'].cleaned_data
                    if 'guard_first_name' in sub_data or ef['prefix'].endswith('guardcontactform'):
                        regProf.contact_guardian = ContactInfo.addOrUpdate(curUser, regProf, sub_data, regProf.contact_guardian, 'guard_')
                    elif 'emerg_first_name' in sub_data or ef['prefix'].endswith('emergcontactform'):
                        regProf.contact_emergency = ContactInfo.addOrUpdate(curUser, regProf, sub_data, regProf.contact_emergency, 'emerg_')

            regProf.save()

            curUser.first_name = new_data.get('first_name')
            curUser.last_name  = new_data.get('last_name')
            curUser.email     = new_data.get('e_mail')
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
            if prog_input is None:
                regProf = RegistrationProfile.getLastProfile(curUser)
            else:
                regProf = RegistrationProfile.getLastForProgram(curUser, prog)
            if regProf.id is None:
                regProf = RegistrationProfile.getLastProfile(curUser)
            if not Tag.getBooleanTag('allow_change_grade_level'):
                if regProf.student_info:
                    if regProf.student_info.dob and 'dob' in form.fields:
                        form.data['dob'] = regProf.student_info.dob
                        form.fields['dob'].widget.attrs['disabled'] = "true"
                        form.fields['dob'].required = False
                    if regProf.student_info.graduation_year and 'graduation_year' in form.fields:
                        form.data['graduation_year'] = regProf.student_info.graduation_year
                        form.fields['graduation_year'].widget.attrs['disabled'] = "true"
                        form.fields['graduation_year'].required = False

    else:
        if prog_input is None:
            regProf = RegistrationProfile.getLastProfile(curUser)
        else:
            regProf = RegistrationProfile.getLastForProgram(curUser, prog)
        if regProf.id is None:
            regProf = RegistrationProfile.getLastProfile(curUser)
        new_data = {}
        if curUser.isStudent():
            new_data['studentrep'] = curUser.groups.filter(name="StudentRep").exists()
        new_data['first_name'] = curUser.first_name
        new_data['last_name']  = curUser.last_name
        new_data['e_mail']     = curUser.email
        new_data = regProf.updateForm(new_data, primary_role)

        if regProf.student_info and regProf.student_info.dob:
            new_data['dob'] = regProf.student_info.dob

        if 'k12school' in new_data and (isinstance(new_data['k12school'], str) or isinstance(new_data['k12school'], str)):
            new_data['unmatched_school'] = True

        #   Set default values for state fields
        state_fields = ['address_state', 'emerg_address_state']
        state_tag_map = {}
        for field in state_fields:
            state_tag_map[field] = 'local_state'
        form = FormClass(curUser, initial=new_data, tag_map=state_tag_map)
        extra_forms = []
        extra_data = {}
        extra_data = regProf.updateForm(extra_data)
        for spec in extra_form_specs:
            if spec.get('takes_user', False):
                ef = spec['form_class'](curUser, initial=extra_data, prefix=spec['prefix'])
            else:
                ef = spec['form_class'](initial=extra_data, prefix=spec['prefix'])
            extra_forms.append({
                'form': ef,
                'role': spec['role'],
                'prefix': spec['prefix'],
                'is_subform': spec.get('is_subform', False),
            })

    context['new_user'] = regProf.id is None
    context['request'] = request
    context['form'] = form
    context['require_student_phonenum'] = Tag.getBooleanTag('require_student_phonenum')
    context['extra_forms'] = extra_forms
    return render_to_response('users/profile.html', request, context)

@login_required
def myesp_onsite(request):
    user = request.user
    if not user.isOnsite():
        raise ESPError('You are not a valid onsite user, please go away.', log=False)

    progs = Permission.program_by_perm(user, "Onsite")

    # Order them decreasing by id
    progs = list(progs.order_by("-id"))

    if len(progs) == 1:
        return HttpResponseRedirect('/onsite/%s/main' % progs[0].getUrlBase())
    else:
        return render_to_response('program/pickonsite.html', request, {'progs': progs})

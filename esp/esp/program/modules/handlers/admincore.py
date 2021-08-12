
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
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db.models.query import Q
from django.forms.formsets import formset_factory
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect

from esp.accounting.controllers import ProgramAccountingController
from esp.program.modules.base import ProgramModuleObj, needs_admin, CoreModule, main_call, aux_call
from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.users.models import Permission
from esp.utils.web import render_to_response
from esp.utils.widgets import DateTimeWidget

from datetime import datetime
from copy import copy
from collections import OrderedDict

class EditPermissionForm(forms.Form):
    start_date = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    end_date = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    skip = forms.BooleanField(required=False, widget=forms.HiddenInput)

class NewPermissionForm(forms.Form):
    permission_type = forms.ChoiceField(choices=filter(lambda x: isinstance(x[1], tuple) and "Deadline" in x[0], Permission.PERMISSION_CHOICES))
    role = forms.ChoiceField(choices = [("Student","Students"),("Teacher","Teachers"),("Volunteer","Volunteers")])
    start_date = forms.DateTimeField(label='Opening date/time', initial=datetime.now, widget=DateTimeWidget(), required=False)
    end_date = forms.DateTimeField(label='Closing date/time', initial=None, widget=DateTimeWidget(), required=False)
    
    def __init__(self, *args, **kwargs):
        extra_roles = kwargs.pop('extra_roles', [])
        super(NewPermissionForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = self.fields['role'].choices + [(role, role) for role in extra_roles]

class AdminCore(ProgramModuleObj, CoreModule):
    doc = """Includes the core views for managing a program (e.g. settings, dashboard)."""

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Program Dashboard",
            "module_type": "manage",
            "seq": -9999,
            "choosable": 1,
            }

    @aux_call
    @needs_admin
    def main(self, request, tl, one, two, module, extra, prog):
        context = {}
        modules = self.program.getModules(request.user, 'manage')

        context['modules'] = sorted(modules, key = lambda pmo: pmo.module.link_title)
        context['one'] = one
        context['two'] = two

        #   Populate context with variables to show which program module views are available
        for (tl, view_name) in prog.getModuleViews():
            context['%s_%s' % (tl, view_name)] = True

        return render_to_response(self.baseDir()+'directory.html', request, context)

    @aux_call
    @needs_admin
    def settings(self, request, tl, one, two, module, extra, prog):
        from esp.program.modules.forms.admincore import ProgramSettingsForm, TeacherRegSettingsForm, StudentRegSettingsForm
        context = {}
        submitted_form = ""
        crmi = ClassRegModuleInfo.objects.get(program=prog)
        scrmi = StudentClassRegModuleInfo.objects.get(program=prog)
        old_url = prog.url
        context['open_section'] = extra

        #If one of the forms was submitted, process it and save if valid
        if request.method == 'POST':
            if 'form_name' in request.POST:
                submitted_form = request.POST['form_name']
                if submitted_form == "program":
                    form = ProgramSettingsForm(request.POST, instance = prog)
                    if form.is_valid():
                        form.save()
                        #If the url for the program is now different, redirect to the new settings page
                        if prog.url is not old_url:
                            return HttpResponseRedirect( '/manage/%s/settings' % (prog.url))
                    prog_form = form
                    context['open_section'] = "program"
                elif submitted_form == "crmi":
                    form = TeacherRegSettingsForm(request.POST, instance = crmi)
                    if form.is_valid():
                        form.save()
                    crmi_form = form
                    context['open_section'] = "crmi"
                elif submitted_form == "scrmi":
                    form = StudentRegSettingsForm(request.POST, instance = scrmi)
                    if form.is_valid():
                        form.save()
                    scrmi_form = form
                    context['open_section'] = "scrmi"
                if form.is_valid():
                    form.save()
                    #If the url for the program is now different, redirect to the new settings page
                    if prog.url is not old_url:
                        return HttpResponseRedirect( '/manage/%s/settings/%s' % (prog.url, context['open_section']))

        #Set up any other forms on the page
        if submitted_form != "program":
            prog_dict = {}
            prog_dict.update(model_to_dict(prog))
            #We need to populate all of these manually
            prog_dict['term'] = prog.program_instance
            prog_dict['term_friendly'] = prog.name.replace(prog.program_type, "", 1).strip()
            prog_dict["program_type"] = prog.program_type
            pac = ProgramAccountingController(prog)
            line_items = pac.get_lineitemtypes(required_only=True).filter(text="Program admission").values('amount_dec')
            prog_dict['base_cost'] = int(sum(x["amount_dec"] for x in line_items))
            prog_dict["sibling_discount"] = prog.sibling_discount
            prog_form = ProgramSettingsForm(prog_dict, instance = prog)

        if submitted_form != "crmi":
            crmi_form = TeacherRegSettingsForm(instance = crmi)

        if submitted_form != "scrmi":
            scrmi_form = StudentRegSettingsForm(instance = scrmi)

        context['one'] = one
        context['two'] = two
        context['program'] = prog
        context['forms'] = [
                            ("Program Settings", "program", prog_form),
                            ("Teacher Registration Settings", "crmi", crmi_form),
                            ("Student Registration Settings", "scrmi", scrmi_form),
                           ]

        return render_to_response(self.baseDir()+'settings.html', request, context)

    @aux_call
    @needs_admin
    def tags(self, request, tl, one, two, module, extra, prog):
        from esp.program.modules.forms.admincore import ProgramTagSettingsForm
        context = {}

        #If one of the forms was submitted, process it and save if valid
        if request.method == 'POST':
            form = ProgramTagSettingsForm(request.POST, program = prog)
            if form.is_valid():
                form.save()
                form = ProgramTagSettingsForm(program = prog) # replace null responses with defaults if processed successfully
        else:
            form = ProgramTagSettingsForm(program = prog)

        context['one'] = one
        context['two'] = two
        context['program'] = prog
        context['form'] = form
        context['categories'] = form.categories
        context['open_section'] = extra

        return render_to_response(self.baseDir()+'tags.html', request, context)

    @main_call
    @needs_admin
    def dashboard(self, request, tl, one, two, module, extra, prog):
        """ The administration panel showing statistics for the program, and a list
        of classes with the ability to edit each one.  """
        context = {}
        modules = self.program.getModules(request.user, 'manage')

        for module in modules:
            context = module.prepare(context)

        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        return render_to_response(self.baseDir()+'mainpage.html', request, context)

    @aux_call
    @needs_admin
    def registrationtype_management(self, request, tl, one, two, module, extra, prog):

        from esp.program.modules.forms.admincore import VisibleRegistrationTypeForm as VRTF
        from django.conf import settings
        from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC

        context = {}
        context['one'] = one
        context['two'] = two
        context['prog'] = prog
        context['POST'] = False
        context['saved'] = False
        context['support'] = settings.DEFAULT_EMAIL_ADDRESSES['support']

        if request.method == 'POST':
            context['POST'] = True
            form = VRTF(request.POST)
            if form.is_valid():
                context['saved'] = RTC.setVisibleRegistrationTypeNames(form.cleaned_data['display_names'], prog)

        display_names = list(RTC.getVisibleRegistrationTypeNames(prog, for_VRT_form=True))
        context['form'] = VRTF(data={'display_names': display_names})
        return render_to_response(self.baseDir()+'registrationtype_management.html', request, context)

    @aux_call
    @needs_admin
    def lunch_constraints(self, request, tl, one, two, module, extra, prog):
        from esp.program.modules.forms.admincore import LunchConstraintsForm
        context = {}
        if request.method == 'POST':
            context['POST'] = True
            form = LunchConstraintsForm(prog, request.POST)
            if form.is_valid():
                form.save_data()
                context['saved'] = True
            else:
                context['saved'] = False
        else:
            form = LunchConstraintsForm(prog)
        context['form'] = form
        return render_to_response(self.baseDir()+'lunch_constraints.html', request, context)

    @aux_call
    @needs_admin
    def deadline_management(self, request, tl, one, two, module, extra, prog):
        #   Define a formset for editing multiple perms simultaneously.
        EditPermissionFormset = formset_factory(EditPermissionForm)

        #   Define a status message
        message = ''

        #   Handle 'open' / 'close' actions
        if extra == 'open' and 'group' in request.GET and 'perm' in request.GET:
            #   If there are no permissions for this permission type, create one and open it now (open ended)
            #   If there are permission(s) for this type, take the most recent(?) and open it (open ended)
            group = Group.objects.get(id = request.GET['group'])
            perms = Permission.objects.filter(role = group, permission_type = request.GET['perm'], program = prog).order_by('-end_date')
            if perms.count() > 0:
                perms[0].unexpire()
            else:
                Permission.objects.create(role = group, permission_type = request.GET['perm'], start_date = datetime.now(), program = prog)
            message = 'Deadline opened for %ss: %s.' % (group, Permission.nice_name_lookup(request.GET['perm']))

        elif extra == 'close' and 'group' in request.GET and 'perm' in request.GET:
            #   If there are open permission(s) for this type, close them all
            group = Group.objects.get(id = request.GET['group'])
            perms = Permission.valid_objects().filter(permission_type = request.GET['perm'], program = prog, role = group)
            perms.update(end_date = datetime.now())
            message = 'Deadline closed for %ss: %s.' % (group, Permission.nice_name_lookup(request.GET['perm']))

        #   Check incoming form data
        if request.method == 'POST' and 'submit' in request.POST:
            if request.POST['submit'] == 'Create Deadline':
                create_form = NewPermissionForm(request.POST.copy())
                if create_form.is_valid():
                    perm = Permission.objects.create(user=None, permission_type=create_form.cleaned_data['permission_type'],
                                                     role=Group.objects.get(name=create_form.cleaned_data['role']),program=prog,
                                                     start_date = create_form.cleaned_data['start_date'], end_date = create_form.cleaned_data['end_date'])
                    message = 'Deadline created for %ss: %s.' % (create_form.cleaned_data['role'], perm.nice_name())
                else:
                    message = 'Error(s) while creating permission: %s' % create_form.errors
            elif request.POST['submit'] == 'Save':
                edit_formset = EditPermissionFormset(request.POST.copy(), prefix='edit')
                if edit_formset.is_valid():
                    num_forms = 0
                    for form in edit_formset.forms:
                        #   Check if the permission with the specified ID exists.
                        if 'id' in form.cleaned_data and not form.cleaned_data['skip'] and Permission.objects.filter(id=form.cleaned_data['id']).exists():
                            num_forms += 1
                            perm = Permission.objects.get(id=form.cleaned_data['id'])
                            perm.start_date = form.cleaned_data['start_date']
                            perm.end_date = form.cleaned_data['end_date']
                            perm.save()
                    if num_forms > 0:
                        message = 'Changes saved.'
                else:
                    message = 'Error(s) while saving permission(s): %s' % edit_formset.errors

        #   find all the existing permissions with this program
        #   Only consider global permissions -- those that apply to all users
        #   of a particular role.  Permissions added for individual users
        #   should be managed in the admin interface.
        perms = Permission.deadlines().filter(program=self.program, user__isnull=True)
        #   Get roles associated with those permissions, plus the normal roles (if not already selected)
        groups = list(Group.objects.filter(Q(id__in=perms.values_list('role', flat = True).distinct()) | Q(name__in=["Student", "Teacher", "Volunteer"])))

        group_perms = {group: {} for group in groups}
        for group in groups:
            #   Insert all of the permission types that could exist for normal roles
            for perm_type in [perm_type for perm_type in Permission.PERMISSION_CHOICES_FLAT if perm_type.startswith(group.name)]:
                group_perms[group][perm_type] =  {'is_open': False, 'perms': []}
            perms_for_group = perms.filter(role = group)
            #   Insert permissions that exist for this role
            #   For each permission, determine which other ones it implies
            for perm in perms_for_group:
                group_perms[group].setdefault(perm.permission_type, {'is_open': False, 'perms': []})['perms'].append(perm)
                implies = Permission.implications.get(perm.permission_type, [])
                for p in implies:
                    if p == perm.permission_type: continue
                    perm_copy = copy(perm)
                    perm_copy.permission_type = p
                    perm_copy.implied = True,
                    perm_copy.implied_by = perm
                    group_perms[group].setdefault(perm_copy.permission_type, {'is_open': False, 'perms': []})['perms'].append(perm_copy)
            group_perms[group] = OrderedDict([(key, group_perms[group][key]) for key in sorted(group_perms[group].keys(), key = Permission.PERMISSION_CHOICES_FLAT.index)])

        #   Populate template context to render page with forms
        context = {}

        initial_data = [perm.__dict__ for group, perm_types in group_perms.items() for perm_type, details in perm_types.items() for perm in details['perms']]
        #   Supply initial data for forms
        formset = EditPermissionFormset(initial = initial_data, prefix = 'edit')
        idx = 0
        for group, perm_types in group_perms.items():
            for perm_type, details in perm_types.items():
                for perm in details['perms']:
                    if perm.is_valid():
                        details['is_open'] = True
                    perm.form = formset.forms[idx]
                    if getattr(perm, "implied", False):
                        perm.form.fields['skip'].initial = True
                        perm.form.fields['start_date'].disabled = True
                        perm.form.fields['end_date'].disabled = True
                    idx += 1
                # Is this permission type implied open? (so it can't be closed with an individual permission)
                details['implied_open'] = any([getattr(perm, "implied", False) and perm.is_valid() for perm in details['perms']])
                details['recursive'] = perm_type in Permission.implications.keys()
                # Sort by validity and start/end dates
                group_perms[group][perm_type]['perms'].sort(key=lambda perm: (perm.is_valid(), perm.end_date or datetime.max, perm.start_date or datetime.min), reverse=True)

        context['message'] = message
        context['manage_form'] = formset.management_form
        context['group_perms'] = group_perms
        context['perms'] = perms
        context['create_form'] = NewPermissionForm(extra_roles = [group.name for group in groups if group.name not in ["Student", "Teacher", "Volunteer"]])

        return render_to_response(self.baseDir()+'deadlines.html', request, context)

    #   Alias for deadline management
    deadlines = deadline_management

    def isStep(self):
        return True

    class Meta:
        proxy = True
        app_label = 'modules'

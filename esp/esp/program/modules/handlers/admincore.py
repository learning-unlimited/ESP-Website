
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

class EditPermissionForm(forms.Form):
    start_date = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    end_date = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    id = forms.IntegerField(required=True, widget=forms.HiddenInput)

class NewPermissionForm(forms.Form):
    permission_type = forms.ChoiceField(choices=filter(lambda x: isinstance(x[1], tuple) and "Deadline" in x[0], Permission.PERMISSION_CHOICES))
    role = forms.ChoiceField(choices = [("Student","Students"),("Teacher","Teachers"),("Volunteer","Volunteers")])
    start_date = forms.DateTimeField(label='Opening date/time', initial=datetime.now, widget=DateTimeWidget(), required=False)
    end_date = forms.DateTimeField(label='Closing date/time', initial=None, widget=DateTimeWidget(), required=False)

class AdminCore(ProgramModuleObj, CoreModule):

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

        context['modules'] = modules
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
            line_items = pac.get_lineitemtypes(required_only=True).values('amount_dec')
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
        if extra == 'open' and 'id' in request.GET:
            perm = Permission.objects.get(id=request.GET['id'])
            #   Clear any duplicate user permissions
            Permission.objects.filter(permission_type=perm.permission_type, program=perm.program, user__isnull=True, role=perm.role).exclude(id=perm.id).delete()
            perm.end_date = None
            perm.save()
            message = 'Deadline opened: %s.' % perm.nice_name()

        elif extra == 'close' and 'id' in request.GET:
            perm = Permission.objects.get(id=request.GET['id'])
            #   Clear any duplicate user permissions
            Permission.objects.filter(permission_type=perm.permission_type, program=perm.program, user__isnull=True, role=perm.role).exclude(id=perm.id).delete()
            perm.end_date = datetime.now()
            perm.save()
            message = 'Deadline closed: %s.' % perm.nice_name()

        #   Check incoming form data
        if request.method == 'POST':
            edit_formset = EditPermissionFormset(request.POST.copy(), prefix='edit')
            create_form = NewPermissionForm(request.POST.copy())
            if edit_formset.is_valid():
                num_forms = 0
                for form in edit_formset.forms:
                    #   Check if the permission with the specified ID exists.
                    #   It may have been deleted by previous iterations of this loop
                    #   deleting duplicate permissions.
                    if 'id' in form.cleaned_data and Permission.objects.filter(id=form.cleaned_data['id']).exists():
                        num_forms += 1
                        perm = Permission.objects.get(id=form.cleaned_data['id'])
                        #   Clear any duplicate perms
                        Permission.objects.filter(permission_type=perm.permission_type, program=perm.program, user__isnull=True, role=perm.role).exclude(id=perm.id).delete()
                        perm.start_date = form.cleaned_data['start_date']
                        perm.end_date = form.cleaned_data['end_date']
                        perm.save()
                if num_forms > 0:
                    message = 'Changes saved.'
            if create_form.is_valid():
                perm, created = Permission.objects.get_or_create(user=None, permission_type=create_form.cleaned_data['permission_type'], role=Group.objects.get(name=create_form.cleaned_data['role']),program=prog)
                if not created:
                    message = 'Deadline already exists: %s.  Please modify the existing deadline.' % perm.nice_name()
                else:
                    perm.start_date = create_form.cleaned_data['start_date']
                    perm.end_date = create_form.cleaned_data['end_date']
                    perm.save()
                    message = 'Deadline created: %s.' % perm.nice_name()
            else:
                message = 'No activities selected.  Please select a deadline type from the list before creating a deadline.'

        #   find all the existing permissions with this program
        #   Only consider global permissions -- those that apply to all users
        #   of a particular role.  Permissions added for individual users
        #   should be managed in the admin interface.
        perms = Permission.deadlines().filter(program=self.program, user__isnull=True)
        perm_map = {p.permission_type: p for p in perms}

        #   Populate template context to render page with forms
        context = {}

        #   Set a flag on each perm for whether it has ended
        #   TODO(benkraft): refactor users to just call is_valid themselves.
        for perm in perms:
            perm.open_now = perm.is_valid()

        #   For each permission, determine which other ones it implies
        for perm in perms:
            includes = Permission.implications.get(perm.permission_type, [])
            perm.includes = []
            perm.name = perm.nice_name()
            for p in includes:
                if p == perm.permission_type: continue
                perm.includes.append({'type':p,'nice_name':Permission.nice_name_lookup(p)})
                if p in perm_map:
                    perm.includes[-1].update({'overridden':True,
                                              'overridden_by':perm_map[p],
                                              'bit_open':perm_map[p].open_now})

        #   Supply initial data for forms
        formset = EditPermissionFormset(initial = [perm.__dict__ for perm in perms], prefix = 'edit')
        for i in range(len(perms)):
            perms[i].form = formset.forms[i]


        context['message'] = message
        context['manage_form'] = formset.management_form
        context['perms'] = perms
        context['create_form'] = NewPermissionForm()

        return render_to_response(self.baseDir()+'deadlines.html', request, context)

    #   Alias for deadline management
    deadlines = deadline_management

    def isStep(self):
        return True

    class Meta:
        proxy = True
        app_label = 'modules'

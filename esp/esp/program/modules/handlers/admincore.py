
from __future__ import absolute_import
from __future__ import print_function
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
from django.contrib.auth.models import Group
from django.db.models.query import Q
from django.forms.formsets import formset_factory
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect
from django.template.defaultfilters import slugify
from django.utils import timezone  # add timezone from local_settings.py in labels

from esp.accounting.controllers import ProgramAccountingController
from esp.cal.models import Event
from esp.db.forms import AjaxForeignKeyNewformField
from esp.program.modules.base import ProgramModuleObj, needs_admin, CoreModule, main_call, aux_call
from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.tagdict.models import Tag
from esp.users.models import Permission, ESPUser
from esp.utils.web import render_to_response
from esp.utils.widgets import DateTimeWidget

from datetime import datetime
from decimal import Decimal
from copy import copy
from collections import OrderedDict


TZINFO = timezone.get_current_timezone()  # get timezone set in local_settings.py
FTIMEZONE = " (" + datetime.now(tz=TZINFO).strftime("%Z") + ")"  # formatted timezone


class EditPermissionForm(forms.Form):
    start_date = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    end_date = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    skip = forms.BooleanField(required=False, widget=forms.HiddenInput)

class NewDeadlineForm(forms.Form):
    deadline_type = forms.ChoiceField(choices=[x for x in Permission.PERMISSION_CHOICES if "Administer" not in x[0]])
    role = forms.ChoiceField(choices = [("Student", "Students"), ("Teacher", "Teachers"), ("Volunteer", "Volunteers")])
    start_date = forms.DateTimeField(label='Opening date/time' + FTIMEZONE, initial=datetime.now, widget=DateTimeWidget(), required=False)
    end_date = forms.DateTimeField(label='Closing date/time' + FTIMEZONE, initial=None, widget=DateTimeWidget(), required=False)

    def __init__(self, *args, **kwargs):
        super(NewDeadlineForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = self.fields['role'].choices + [(role, role + "s") for role in Group.objects.exclude(name__in=["Student", "Teacher", "Volunteer"]
                                                                                                                          ).order_by('name').values_list('name', flat = True)]

class NewPermissionForm(forms.Form):
    permission_type = forms.ChoiceField(choices=[x for x in Permission.PERMISSION_CHOICES if "Administer" not in x[0]])
    user = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='user', label='User',
        help_text='Start typing a username or "Last Name, First Name", then select the user from the dropdown.')
    perm_start_date = forms.DateTimeField(label='Opening date/time' + FTIMEZONE, initial=datetime.now, widget=DateTimeWidget(), required=False)
    perm_end_date = forms.DateTimeField(label='Closing date/time' + FTIMEZONE, initial=None, widget=DateTimeWidget(), required=False)

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
        required_steps = [
                          ('TeacherQuizModule', "Set up the teacher logistics quiz", "/customforms/", Tag.getProgramTag('quiz_form_id', self.program)),
                          ('TeacherCustomFormModule', "Set up the teacher custom form", "/customforms/", Tag.getProgramTag('teach_extraform_id', self.program)),
                          ('StudentCustomFormModule', "Set up the student custom form", "/customforms/", Tag.getProgramTag('learn_extraform_id', self.program)),
                          ('StudentLunchSelection', "Set up multiple lunch periods", '/manage/' + self.program.url + '/lunch_constraints', Event.objects.filter(meeting_times__parent_class__parent_program=self.program, meeting_times__parent_class__category__category='Lunch').exists()),
                         ] # (handler, setup title, setup path, isCompleted)
        extra_steps = [step for step in required_steps if prog.hasModule(step[0])]
        optional_steps = [
                          ('ProgramPrintables', "Format printable student schedules", '/manage/' + self.program.url + '/studentscheduleform', Tag.getProgramTag('student_schedule_format', self.program)),
                          ('StudentSurveyModule', "Set up the student post-program survey", '/manage/' + self.program.url + '/surveys', self.program.getSurveys().filter(category = "learn").exists()),
                          ('TeacherSurveyModule', "Set up the teacher post-program survey", '/manage/' + self.program.url + '/surveys', self.program.getSurveys().filter(category = "teach").exists()),
                          ('VolunteerSignup', "Set up volunteer signup", '/manage/' + self.program.url + '/volunteering', self.program.getVolunteerRequests().exists()),
                         ] # (handler, setup title, setup path, isCompleted)
        extra_steps_optional = [step for step in optional_steps if prog.hasModule(step[0])]

        context['modules'] = modules
        context['extra_steps'] = extra_steps
        context['extra_steps_optional'] = extra_steps_optional
        context['modules_alph'] = sorted(modules, key = lambda pmo: pmo.module.link_title)
        context['one'] = one
        context['two'] = two

        #   Populate context with variables to show which program module views are available
        for (tl, view_name) in prog.getModuleViews():
            context['%s_%s' % (tl, view_name)] = True

        return render_to_response(self.baseDir()+'directory.html', request, context)

    @aux_call
    @needs_admin
    def settings(self, request, tl, one, two, module, extra, prog):
        from esp.program.modules.forms.admincore import ProgramSettingsForm, TeacherRegSettingsForm, StudentRegSettingsForm, ReceiptsForm
        context = {}
        submitted_form = ""
        crmi = ClassRegModuleInfo.objects.get(program=prog)
        scrmi = StudentClassRegModuleInfo.objects.get(program=prog)
        old_url = prog.url
        context['open_section'] = extra
        forms = {}

        #If one of the forms was submitted, process it and save if valid
        if request.method == 'POST':
            if 'form_name' in request.POST:
                submitted_form = request.POST['form_name']
                if submitted_form == "program":
                    form = ProgramSettingsForm(request.POST, instance = prog)
                    if form.is_valid():
                        new_prog = form.save()
                        # update related things
                        pac = ProgramAccountingController(new_prog)
                        line_item = pac.default_admission_lineitemtype()
                        line_item.amount_dec=Decimal('%.2f' % form.cleaned_data['base_cost'])
                        line_item.save()
                        line_item.transfer_set.all().update(amount_dec=Decimal('%.2f' % form.cleaned_data['base_cost']))
                        def_account = pac.default_program_account()
                        def_account.name = slugify(new_prog.name)
                        def_account.save()
                        new_prog.sibling_discount = form.cleaned_data['sibling_discount']
                        new_prog.save()
                        #If the url for the program is now different, redirect to the new settings page
                        if new_prog.url is not old_url:
                            return HttpResponseRedirect( '/manage/%s/settings/program' % (new_prog.url))
                    else:
                        forms['program'] = form
                    context['open_section'] = "program"
                elif submitted_form == "crmi":
                    form = TeacherRegSettingsForm(request.POST, instance = crmi)
                    if form.is_valid():
                        form.save()
                    else:
                        forms['crmi'] = form
                    context['open_section'] = "crmi"
                elif submitted_form == "scrmi":
                    form = StudentRegSettingsForm(request.POST, instance = scrmi)
                    if form.is_valid():
                        form.save()
                    else:
                        forms['scrmi'] = form
                    context['open_section'] = "scrmi"
                elif submitted_form == "receipts":
                    form = ReceiptsForm(request.POST, program = prog)
                    if form.is_valid():
                        form.save()
                    else:
                        forms['receipts'] = form
                    context['open_section'] = "receipts"

        #Set up any other forms on the page
        if "program" not in forms:
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
            forms['program'] = ProgramSettingsForm(prog_dict, instance = prog)

        if "crmi" not in forms:
            forms['crmi'] = TeacherRegSettingsForm(instance = crmi)

        if "scrmi" not in forms:
            forms['scrmi'] = StudentRegSettingsForm(instance = scrmi)

        if "receipts" not in forms:
            forms['receipts'] = ReceiptsForm(program = prog)

        context['one'] = one
        context['two'] = two
        context['program'] = prog
        context['forms'] = [
                            ("Program Settings", "program", forms['program']),
                            ("Teacher Registration Settings", "crmi", forms['crmi']),
                            ("Student Registration Settings", "scrmi", forms['scrmi']),
                            ("Registration Receipts", "receipts", forms['receipts'])
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
        create_form = NewDeadlineForm()
        perm_form = NewPermissionForm()

        #   Define good and bad status messages
        message_good = ''
        message_bad = ''

        #   Handle 'open' / 'close' / 'delete' actions
        if extra == 'open':
            #   If there are no permissions for this permission type, create one and open it now (open ended)
            #   If there are permission(s) for this type, take the most recent(?) and open it (open ended)
            if 'group' in request.GET and 'perm' in request.GET:
                group = Group.objects.get(id = request.GET['group'])
                perms = Permission.objects.filter(role = group, permission_type = request.GET['perm'], program = prog).order_by('-end_date')
                if perms.count() > 0:
                    perms[0].unexpire()
                else:
                    Permission.objects.create(role = group, permission_type = request.GET['perm'], start_date = datetime.now(), program = prog)
                message_good = 'Deadline opened for %ss: %s.' % (group, Permission.nice_name_lookup(request.GET['perm']))
            elif 'perm_id' in request.GET:
                perms = Permission.objects.filter(id=request.GET['perm_id'])
                if perms.count() == 1:
                    perm = perms[0]
                    perm.unexpire()
                    message_good = 'Permission opened for %s: %s.' % (perm.user, perm.nice_name())
                else:
                    message_bad = 'No permission with ID %s.' % (request.GET['perm_id'])

        elif extra == 'close':
            #   If there are open permission(s) for this type, close them all
            if 'group' in request.GET and 'perm' in request.GET:
                group = Group.objects.get(id = request.GET['group'])
                perms = Permission.valid_objects().filter(permission_type = request.GET['perm'], program = prog, role = group)
                perms.update(end_date = datetime.now())
                message_good = 'Deadline closed for %ss: %s.' % (group, Permission.nice_name_lookup(request.GET['perm']))
            if 'perm_id' in request.GET:
                perms = Permission.objects.filter(id=request.GET['perm_id'])
                if perms.count() == 1:
                    perm = perms[0]
                    perm.expire()
                    message_good = 'Permission closed for %s: %s.' % (perm.user, perm.nice_name())
                else:
                    message_bad = 'No permission with ID %s.' % (request.GET['perm_id'])

        elif extra == 'delete' and 'perm_id' in request.GET:
            #   Delete the specified permission if it exists
            perms = Permission.objects.filter(id=request.GET['perm_id'])
            if perms.count() == 1:
                perm = perms[0]
                if 'deadline' in request.GET:
                    message_good = 'Deadline deleted for %ss: %s.' % (perm.role, perm.nice_name())
                else:
                    message_good = 'Permission deleted for %s: %s.' % (perm.user, perm.nice_name())
                perm.delete()
            else:
                if 'deadline' in request.GET:
                    message_bad = 'Error while deleting deadline with ID %s.' % request.GET['perm_id']
                else:
                    message_bad = 'Error while deleting permission with ID %s.' % request.GET['perm_id']

        #   Check incoming form data
        if request.method == 'POST' and 'action' in request.POST:
            if request.POST['action'] == 'add_deadline':
                create_form = NewDeadlineForm(request.POST.copy())
                if create_form.is_valid():
                    perm = Permission.objects.create(user=None, permission_type=create_form.cleaned_data['deadline_type'],
                                                     role=Group.objects.get(name=create_form.cleaned_data['role']), program=prog,
                                                     start_date = create_form.cleaned_data['start_date'], end_date = create_form.cleaned_data['end_date'])
                    message_good = 'Deadline created for %ss: %s.' % (create_form.cleaned_data['role'], perm.nice_name())
                    create_form = NewDeadlineForm()
                else:
                    message_bad = 'Error(s) while creating deadline (see below)'
            elif request.POST['action'] == "add_permission":
                perm_form = NewPermissionForm(request.POST.copy())
                if perm_form.is_valid():
                    perm = Permission.objects.create(user=perm_form.cleaned_data['user'], permission_type=perm_form.cleaned_data['permission_type'], program=prog,
                                                     start_date = perm_form.cleaned_data['perm_start_date'], end_date = perm_form.cleaned_data['perm_end_date'])
                    message_good = 'Permission created for %s: %s.' % (perm_form.cleaned_data['user'], perm.nice_name())
                    perm_form = NewPermissionForm()
                else:
                    message_bad = 'Error(s) while creating permission (see below)'
            elif request.POST['action'] == 'save_deadlines':
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
                        message_good = 'Deadlines saved.'
                else:
                    message_bad = 'Error(s) while saving deadline(s): %s' % edit_formset.errors
            elif request.POST['action'] == 'save_permissions':
                edit_formset = EditPermissionFormset(request.POST.copy(), prefix='edit_perms')
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
                        message_good = 'Permissions saved.'
                else:
                    message_bad = 'Error(s) while saving permission(s): %s' % edit_formset.errors

        #   find all the existing user group permissions for this program
        perms = Permission.objects.filter(program=self.program, user__isnull=True, permission_type__in=Permission.PERMISSION_CHOICES_FLAT).exclude(permission_type="Administer")
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
            group_perms[group] = OrderedDict([(key, group_perms[group][key]) for key in sorted(list(group_perms[group].keys()), key = Permission.PERMISSION_CHOICES_FLAT.index)])

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
                details['recursive'] = perm_type in list(Permission.implications.keys())
                # Sort by validity and start/end dates
                group_perms[group][perm_type]['perms'].sort(key=lambda perm: (perm.is_valid(), perm.end_date or datetime.max, perm.start_date or datetime.min), reverse=True)

        #   find all the existing user permissions for this program
        ind_perms = Permission.objects.filter(program=self.program, user__isnull=False).order_by('user__username', 'permission_type')

        perm_initial_data = [perm.__dict__ for perm in ind_perms]
        perm_formset = EditPermissionFormset(initial = perm_initial_data, prefix = 'edit_perms')
        idx = 0
        for perm in ind_perms:
            perm.form = perm_formset.forms[idx]
            idx += 1

        #   Populate template context to render page with forms
        context = {}
        context['message_good'] = message_good
        context['message_bad'] = message_bad
        context['manage_form'] = formset.management_form
        context['deadlines'] = group_perms
        context['perm_manage_form'] = perm_formset.management_form
        context['permissions'] = ind_perms
        context['create_form'] = create_form
        context['create_perm_form'] = perm_form

        return render_to_response(self.baseDir()+'deadlines.html', request, context)

    #   Alias for deadline management
    deadlines = deadline_management

    @aux_call
    @needs_admin
    def modules(self, request, tl, one, two, module, extra, prog):
        context = {}

        if request.method == 'POST':
            if "default_seq" in request.POST or "default_req" in request.POST or "default_lab" in request.POST:
                # Reset some or all values for learn and teach modules
                for pmo in [mod for mod in prog.getModules(tl = 'learn') if mod.inModulesList()]:
                    pmo = ProgramModuleObj.objects.get(id=pmo.id) # Get the uncached object to make sure we trigger the cache
                    if "default_seq" in request.POST: # Reset module seq values
                        pmo.seq = pmo.module.seq
                    if "default_req" in request.POST: # Reset module required values
                        pmo.required = pmo.module.required
                    if "default_lab" in request.POST: # Reset module required label values
                        pmo.required_label = ""
                    pmo.save()
                for pmo in [mod for mod in prog.getModules(tl = 'teach') if mod.inModulesList()]:
                    pmo = ProgramModuleObj.objects.get(id=pmo.id) # Get the uncached object to make sure we trigger the cache
                    if "default_seq" in request.POST: # Reset module seq values
                        pmo.seq = pmo.module.seq
                    if "default_req" in request.POST: # Reset module required values
                        pmo.required = pmo.module.required
                    if "default_lab" in request.POST: # Reset module required label values
                        pmo.required_label = ""
                    pmo.save()

            # If the sequence form was submitted, process it and update program modules
            learn_req = [mod for mod in request.POST.get("learn_req", "").split(",") if mod]
            learn_not_req = [mod for mod in request.POST.get("learn_not_req", "").split(",") if mod]
            teach_req = [mod for mod in request.POST.get("teach_req", "").split(",") if mod]
            teach_not_req = [mod for mod in request.POST.get("teach_not_req", "").split(",") if mod]
            # Set student registration module sequence and requiredness
            # Also set requirement labels if supplied
            seq = 12 # In case there are other modules that aren't steps and should be earlier
            for mod_id in learn_req:
                pmo = ProgramModuleObj.objects.get(id=mod_id)
                pmo.seq = seq
                seq += 1
                pmo.required = True
                pmo.required_label = request.POST.get("%s_label" % mod_id, "")
                pmo.save()
            for mod_id in learn_not_req:
                pmo = ProgramModuleObj.objects.get(id=mod_id)
                pmo.seq = seq
                seq += 1
                pmo.required = False
                pmo.required_label = request.POST.get("%s_label" % mod_id, "")
                pmo.save()
            # Set teacher registration module sequence and requiredness
            seq = 12 # In case there are other modules that aren't steps and should be earlier
            for mod_id in teach_req:
                pmo = ProgramModuleObj.objects.get(id=mod_id)
                pmo.seq = seq
                seq += 1
                pmo.required = True
                pmo.required_label = request.POST.get("%s_label" % mod_id, "")
                pmo.save()
            for mod_id in teach_not_req:
                pmo = ProgramModuleObj.objects.get(id=mod_id)
                pmo.seq = seq
                seq += 1
                pmo.required = False
                pmo.required_label = request.POST.get("%s_label" % mod_id, "")
                pmo.save()
            # Override some settings that shouldn't be changed
            # Profile modules should always be required and always first
            pmos = ProgramModuleObj.objects.filter(program = prog, module__handler = "RegProfileModule")
            for pmo in pmos:
                pmo.seq = 0
                pmo.required = True
                pmo.save()
            # Credit card modules should never be required and always last
            pmos = ProgramModuleObj.objects.filter(program = prog, module__handler__contains = "CreditCardModule_")
            for pmo in pmos:
                pmo.seq = 10000
                pmo.required = False
                pmo.save()
            # The confirm reg module should never be required
            pmos = ProgramModuleObj.objects.filter(program = prog, module__handler = "StudentRegConfirm")
            for pmo in pmos:
                pmo.required = False
                pmo.save()
            # The availability module should always be required
            pmos = ProgramModuleObj.objects.filter(program = prog, module__handler = "AvailabilityModule")
            for pmo in pmos:
                pmo.required = True
                pmo.save()
            # The acknowledgment modules should always be required
            pmos = ProgramModuleObj.objects.filter(program = prog, module__handler__contains = "AcknowledgementModule")
            for pmo in pmos:
                pmo.required = True
                pmo.save()
            # The two phase lottery module should always be required
            pmos = ProgramModuleObj.objects.filter(program = prog, module__handler = "StudentRegTwoPhase")
            for pmo in pmos:
                pmo.required = True
                pmo.save()

        learn_modules = [mod for mod in prog.getModules(tl = 'learn') if mod.inModulesList()]
        context['learn_modules'] = {'required': [mod for mod in learn_modules if mod.required],
                                    'not_required': [mod for mod in learn_modules if not mod.required]}
        teach_modules = [mod for mod in prog.getModules(tl = 'teach') if mod.inModulesList()]
        context['teach_modules'] = {'required': [mod for mod in teach_modules if mod.required],
                                    'not_required': [mod for mod in teach_modules if not mod.required]}
        context['one'] = one
        context['two'] = two
        context['program'] = prog

        return render_to_response(self.baseDir()+'modules.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

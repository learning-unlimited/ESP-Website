
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, CoreModule, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.datatree.models import *
from esp.users.models import User, UserBit
from django import forms
from django.forms.formsets import formset_factory

from esp.utils.forms import new_callback, grouped_as_table, add_fields_to_class
from esp.utils.widgets import DateTimeWidget
from esp.middleware import ESPError
from esp.datatree.forms import AjaxTreeField

from datetime import datetime

class EditUserbitForm(forms.Form):
    startdate = forms.DateTimeField(widget=DateTimeWidget())
    enddate = forms.DateTimeField(widget=DateTimeWidget(), required=False)
    recursive = forms.ChoiceField(choices=((True, 'Recursive'), (False, 'Individual')), widget=forms.RadioSelect, required=False) 
    id = forms.IntegerField(required=True, widget=forms.HiddenInput)

class NewUserbitForm(forms.Form):
    verb = AjaxTreeField(label='Activity', root_uri="V/Deadline/Registration")
    startdate = forms.DateTimeField(label='Opening date/time', initial=datetime.now, widget=DateTimeWidget())
    enddate = forms.DateTimeField(label='Closing date/time', initial=datetime(9999, 01, 01), widget=DateTimeWidget(), required=False)
    recursive = forms.ChoiceField(label='Scope', choices=((True, 'Recursive'), (False, 'Individual')), initial=False, widget=forms.RadioSelect, required=False) 

class AdminCore(ProgramModuleObj, CoreModule):

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Program Dashboard",
            "module_type": "manage",
            "main_call": "dashboard",
            "aux_calls": "deadlines",
            "seq": -9999
            }

    @aux_call
    @needs_admin
    def main(self, request, tl, one, two, module, extra, prog):
        context = {}
        modules = self.program.getModules(self.user, 'manage')
                    
        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        return render_to_response(self.baseDir()+'directory.html', request, (prog, tl), context)

    @main_call
    @needs_admin
    def dashboard(self, request, tl, one, two, module, extra, prog):
        """ The administration panel showing statistics for the program, and a list
        of classes with the ability to edit each one.  """
        context = {}
        modules = self.program.getModules(self.user, 'manage')
        
        for module in modules:
            context = module.prepare(context)
 
        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def deadline_management(self, request, tl, one, two, module, extra, prog):
        #   Define a formset for editing multiple user bits simultaneously.
        EditUserbitFormset = formset_factory(EditUserbitForm)
    
        #   Define a status message
        message = ''
    
        #   Handle 'open' / 'close' actions
        if extra == 'open' and 'id' in request.GET:
            bit = UserBit.objects.get(id=request.GET['id'])
            bit.renew()
            message = 'Deadline opened: %s.' % bit.verb.friendly_name
        elif extra == 'close' and 'id' in request.GET:
            bit = UserBit.objects.get(id=request.GET['id'])
            bit.expire()
            message = 'Deadline closed: %s.' % bit.verb.friendly_name

        #   Check incoming form data
        if request.method == 'POST':
            edit_formset = EditUserbitFormset(request.POST.copy(), prefix='edit')
            create_form = NewUserbitForm(request.POST.copy())
            if edit_formset.is_valid(): 
                num_forms = 0
                for form in edit_formset.forms:
                    if 'id' in form.cleaned_data:
                        num_forms += 1
                        bit = UserBit.objects.get(id=form.cleaned_data['id'])
                        bit.startdate = form.cleaned_data['startdate']
                        bit.enddate = form.cleaned_data['enddate']
                        bit.recursive = (form.cleaned_data['recursive'] == u'True')
                        bit.save()
                if num_forms > 0:
                    message = 'Changes saved.'
            if create_form.is_valid():
                bit, created = UserBit.objects.get_or_create(user=None, verb=create_form.cleaned_data['verb'], qsc=prog.anchor)
                if not created:
                    message = 'Deadline already exists: %s.  Please modify the existing deadline.' % bit.verb.friendly_name
                else:
                    bit.startdate = create_form.cleaned_data['startdate']
                    bit.enddate = create_form.cleaned_data['enddate']
                    bit.recursive = (create_form.cleaned_data['recursive'] == u'True')
                    bit.save()
                    message = 'Deadline created: %s.' % bit.verb.friendly_name
            else:
                message = 'No activities selected.  Please select a deadline type from the tree before creating a deadline.'
    
        #   Get a list of Datatree nodes corresponding to user bit verbs
        deadline_verb = GetNode("V/Deadline/Registration")
        nodes = deadline_verb.descendants().exclude(id=deadline_verb.id).order_by('uri')

        #   Build a list of user bits that reference the relevant verbs
        bits = []
        bit_map = {}
        for v in nodes:
            selected_bits = UserBit.objects.filter(qsc=self.program_anchor_cached(), verb=v, user__isnull=True).order_by('-id')
            if selected_bits.count() > 0:
                bits.append(selected_bits[0])
                bit_map[v.uri] = bits[-1]

        #   Populate template context to render page with forms
        context = {}

        #   Set a flag on each bit for whether it is currently open
        for bit in bits:
            if bit.enddate > datetime.now():
                bit.open_now = True
            else:
                bit.open_now = False
        #   For each bit B, get a list of other bits that B overrides or are overriden by B
        for bit in bits:
            bit.uri_rel = bit.verb.uri[(len(deadline_verb.uri) + 1):]
            bit.includes = bit.verb.descendants().exclude(id=bit.verb.id)
            for node in bit.includes:
                if node in nodes and node.uri in bit_map:
                    node.overridden = True
                    node.overridden_by = bit_map[node.uri]
                    node.bit_open = bit_map[node.uri].open_now
            
        #   Supply initial data from user bits for forms
        formset = EditUserbitFormset(initial=[bit.__dict__ for bit in bits], prefix='edit')
        for i in range(len(bits)):
            bits[i].form = formset.forms[i]
        
        context['message'] = message
        context['manage_form'] = formset.management_form
        context['bits'] = bits
        context['create_form'] = NewUserbitForm()
        
        return render_to_response(self.baseDir()+'deadlines.html', request, (prog, tl), context) 
        
    #   Alias for deadline management
    deadlines = deadline_management
        
    def isStep(self):
        return True
    
 


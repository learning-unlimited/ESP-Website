
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
from esp.datatree.models import DataTree, GetNode
from esp.users.models import User, UserBit
from django import forms
from esp.utils.forms import new_callback, grouped_as_table, add_fields_to_class
from esp.middleware import ESPError



class UserBitForm(forms.ModelForm):
    def __init__(self, bit = None, *args, **kwargs):
        super(UserBitForm, self).__init__(*args, **kwargs)

        if bit != None:
            self.fields['startdate'] = forms.DateTimeField(initial=bit.startdate)
            self.fields['enddate'] = forms.DateTimeField(initial=bit.enddate, required=False)
            self.fields['id'] = forms.IntegerField(initial=bit.id, widget=forms.HiddenInput())
            self.fields['qsc'] = forms.ModelChoiceField(queryset=DataTree.objects.all(), initial=bit.qsc.id, widget=forms.HiddenInput())
            self.fields['verb'] = forms.ModelChoiceField(queryset=DataTree.objects.all(), initial=bit.verb.id, widget=forms.HiddenInput())
        else:
            self.fields['startdate'] = forms.DateTimeField(required=False)
            self.fields['enddate'] = forms.DateTimeField(required=False)
            self.fields['id'] = forms.IntegerField(widget=forms.HiddenInput())

        self.fields['user'] = forms.ModelChoiceField(queryset=User.objects.all(), widget=forms.HiddenInput(), required=False)
        
        self.fields['startdate'].line_group = 1
        self.fields['enddate'].line_group = 1
        self.fields['recursive'] = forms.BooleanField(label = 'Covers deadlines beneath it ("Recursive")', required=False) # I consider this a bug, though it makes sense in context of the form protocol: Un-checked BooleanFields are marked as having not been filled out
        self.fields['recursive'].line_group = 2
        
    as_table = grouped_as_table
    
    class Meta:
        model = UserBit

class AdminCore(ProgramModuleObj, CoreModule):

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Program Dashboard",
            "module_type": "manage",
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
        """ View for controlling program deadlines (V/Deadline/Registration/*) """
        deadline_verb = GetNode("V/Deadline/Registration")
        
        def add_tree_nodes_to_list(node):
            retVal = []

            for i in node.children():
                retVal.append(i)
                retVal += add_tree_nodes_to_list(i)

            return retVal

        def try_else(fn1, fn2):
            try:
                return fn1()
            except:
                return fn2()

        def mux_bit_to_dict(bit):
            return { 'startdate': bit.startdate, 'enddate': bit.enddate, 'recursive': bit.recursive }

        from django import forms
        
        nodes = add_tree_nodes_to_list(deadline_verb)

        saved_successfully = "not_saving"
        
        if request.method == "POST":
            saved_successfully = False
            
            forms = [ { 'verb': v,
                        'ub_form': UserBitForm(None, request.POST, prefix = "%d_"%v.id),
                        'delete_status': request.POST.has_key("delete_bit_%d" % v.id) and request.POST['delete_bit_%d' % v.id] != ""
                        }
                      for v in nodes ]

            print "test1"
            
            for form in forms:
                # Get rid of any bits we're deleting
                if form['delete_status']:
                    for bit in UserBit.objects.filter(qsc=self.program_anchor_cached(),
                                                      verb=v,
                                                      user__isnull=True):
                        bit.expire()
                print "test2"
                # Save any bits we're updating
                if not form['delete_status'] and form['ub_form'].is_valid():
                    bit = form['ub_form'].save(commit=False)
                    bit.verb = form['verb']
                    bit.qsc = self.program_anchor_cached()
                    bit.user = None
                    if UserBit.objects.filter(qsc=bit.qsc, verb=bit.verb, user__isnull=True).count() > 0:
                        preexist_bit = UserBit.objects.filter(qsc=bit.qsc, verb=bit.verb, user__isnull=True)[0]
                        preexist_bit.startdate = bit.startdate
                        preexist_bit.enddate = bit.enddate
                        preexist_bit.recursive = bit.recursive
                        preexist_bit.save()
                    else:
                        bit.save()
                    
                    saved_successfully = True
            print "test3"
        else:
            forms = [ { 'verb': v,
                        'ub_form': try_else( lambda: UserBitForm( UserBit.objects.get(qsc=self.program_anchor_cached(),
                                                                                      verb=v,
                                                                                      user__isnull=True),
                                                                  prefix = "%d_"%v.id ),
                                             lambda: UserBitForm( prefix = "%d_"%v.id ) )
                        }
                      for v in nodes ]

            for f in forms:
                f['delete_status'] = ( UserBit.objects.filter( qsc=self.program_anchor_cached(),
                                                               verb=f['verb'],
                                                               user__isnull = True ).count() == 0 )
        context= {}
                
        context['userbit_forms'] = forms
        context['saved_successfully'] = saved_successfully
        
        return render_to_response(self.baseDir()+'deadlines.html', request, (prog, tl), context)        
        
        
    def isStep(self):
        return True
    
 


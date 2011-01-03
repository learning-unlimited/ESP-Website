
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.web.util        import render_to_response
from esp.users.models   import ESPUser, User, UserBit
from esp.datatree.models import *
from esp.datatree.sql.query_utils import QTree
from django.db.models.query      import Q
from django import forms

class UserAttributeGetter(object):
    @staticmethod
    def getFunctions():
        """ Enter labels for available fields here; they are sorted alphabetically by key """
        labels = {  '01_id': 'ID',
                    '02_address': 'Address',
                    '03_fullname': 'Full Name',
                    '04_lastname': 'Last Name',
                    '05_firstname': 'First Name',
                    '06_email': 'E-mail',
                    '07_accountdate': 'Created Date',
                    '08_first_regdate': 'Initial Registration Date',
                    '09_last_regdate': 'Most Recent Registration Date',
                    '10_cellphone': 'Cell Phone',
                    '11_textmsg': 'Text Msg?',
                    '12_studentrep': 'Student Rep?',
                    '13_classhours': 'Num Class Hrs',
                    '14_gradyear': 'Grad Year',
                    '15_school': 'School',
                    '16_heard_about': 'Heard about Splash from',
                    '17_transportation': 'Plan to Get to Splash',
                    '18_post_hs': 'Post-HS plans',
                    '19_schoolsystem_id': 'School system ID',
                 }

        last_label_index = len(labels)
        for i in range(3):#replace 3 with call to get_max_applications + fix that method    
            key = str(last_label_index + i + 1) + '_class_application_' + str(i+1)
            labels[key] = 'Class Application ' + str(i+1)
        result = {}
        for item in dir(UserAttributeGetter):
            label_map = {}
            for x in labels.keys():
                label_map[x[3:]] = x
            if item.startswith('get_') and item[4:] in label_map:
                result[label_map[item[4:]]] = labels[label_map[item[4:]]]
            
        return result
    
    def __init__(self, user, program):
        self.user = ESPUser(user)
        self.program = program
        self.profile = self.user.getLastProfile()
        
    def get(self, attr):
        attr = attr.lstrip('0123456789_')
        #if attr = 'classapplication':
            
        result = getattr(self, 'get_' + attr)()
        if result is None:
            return 'N/A'
        else:
            if result is True:
                return 'Yes'
            elif result is False:
                return 'No'
            else:
                return result

    def get_id(self):
        return self.user.id
        
    def get_address(self):
        if self.profile.contact_user:
            return self.profile.contact_user.address()
    
    def get_fullname(self):
        return self.user.name()
        
    def get_lastname(self):
        return self.user.last_name
        
    def get_firstname(self):
        return self.user.first_name
        
    def get_email(self):
        return self.user.email
        
    def get_accountdate(self):
        return self.user.date_joined.strftime("%m/%d/%Y")
        
    def get_regdate(self, ordering='startdate'):
        reg_verb = GetNode('V/Flags/Registration/Enrolled')
        reg_node_parent = self.program.anchor['Classes']
        bits = UserBit.valid_objects().filter(user=self.user, verb=reg_verb).filter(QTree(qsc__below=reg_node_parent))
        if bits.exists():
            return bits.order_by(ordering).values_list('startdate', flat=True)[0].strftime("%Y-%m-%d %H:%M:%S")

    def get_first_regdate(self):
        return self.get_regdate(ordering='startdate')
        
    def get_last_regdate(self):
        return self.get_regdate(ordering='-startdate')

    def get_cellphone(self):
        if self.profile.contact_user:
            return self.profile.contact_user.phone_cell
            
    def get_textmsg(self):
        if self.profile.contact_user:
            return self.profile.contact_user.receive_txt_message
            
    def get_studentrep(self):
        if self.profile.student_info:
            return self.profile.student_info.studentrep

    def get_classhours(self):
        return sum([x.meeting_times.count() for x in self.user.getEnrolledSections(self.program)])
        
    def get_school(self):
        if self.profile.student_info:
            if self.profile.student_info.k12school:
                return self.profile.student_info.k12school.name
            else:
                return self.profile.student_info.school
                
    def get_heard_about(self):
        if self.profile.student_info:
            return self.profile.student_info.heard_about
            
    def get_gradyear(self):
        if self.profile.student_info:
            return self.profile.student_info.graduation_year
            
    def get_transportation(self):
        if self.profile.student_info:
            return self.profile.student_info.transportation
            
    def get_post_hs(self):
        if self.profile.student_info:
            return self.profile.student_info.post_hs

    def get_schoolsystem_id(self):
        if self.profile.student_info:
            return self.profile.student_info.schoolsystem_id

    #Replace this with something based on presence and number of application questions for a particular program 
    def get_max_applications(self):
        return 3

    def get_class_application_1(self):
        responses = self.user.listAppResponses(self.program)
        if len(responses) > 0:
            return str(responses[0].question.subject) + ':  ' + str(responses[0])   
        else:
            return None

    def get_class_application_2(self):
        responses = self.user.listAppResponses(self.program)
        if len(responses) > 1:
            return str(responses[1].question.subject) + ':  ' + str(responses[0])   
        else:
            return None
    def get_class_application_3(self):
        responses = self.user.listAppResponses(self.program)
        if len(responses) > 2:
            return str(responses[2].question.subject) + ':  ' + str(responses[0])   
        else:
            return None

            
class ListGenForm(forms.Form):
    attr_choices = choices=UserAttributeGetter.getFunctions().items()
    attr_choices.sort(key=lambda x: x[0])

    fields = forms.MultipleChoiceField(choices=attr_choices, initial=['id','fullname','address','cellphone','school'], widget=forms.CheckboxSelectMultiple)
    output_type = forms.ChoiceField(choices=(('csv', 'CSV format'), ('html', 'HTML format')), initial='html')

class ListGenModule(ProgramModuleObj):
    """ While far from complete, this will allow you to just generate a simple list of users matching a criteria (criteria very similar to the communications panel)."""
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "User List Generator",
            "link_title": "Generate List of Users",
            "module_type": "manage",
            "seq": 500
            }

    @main_call
    @needs_admin
    def selectList(self, request, tl, one, two, module, extra, prog):
        """ Select the type of list that is requested. """
        from esp.users.views     import get_user_list
        from esp.users.models    import User
        from esp.users.models import PersistentQueryFilter

        if not request.GET.has_key('filterid'):
            filterObj, found = get_user_list(request, self.program.getLists(True))
        else:
            filterid  = request.GET['filterid']
            filterObj = PersistentQueryFilter.getFilterFromID(filterid, User)
            found     = True
        if not found:
            return filterObj

        if request.method == 'POST' and 'fields' in request.POST:
            form = ListGenForm(request.POST)
            if form.is_valid():

                labels_dict = UserAttributeGetter.getFunctions()
                fields = [labels_dict[f] for f in form.cleaned_data['fields']]
                fields.append('Class Application 1')
                output_type = form.cleaned_data['output_type']
            
                users = list(ESPUser.objects.filter(filterObj.get_Q()).filter(is_active=True).distinct())
                users.sort()
                for u in users:
                    ua = UserAttributeGetter(u, self.program)
                    user_fields = [ua.get(x) for x in form.cleaned_data['fields']]
                    u.fields = user_fields

                return render_to_response(self.baseDir()+('list_%s.html' % output_type), request, (prog, tl), {'users': users, 'fields': fields, 'listdesc': filterObj.useful_name})
            else:
                return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {'form': form, 'filterid': filterObj.id})
        else:
            form = ListGenForm()
            return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {'form': form, 'filterid': filterObj.id})


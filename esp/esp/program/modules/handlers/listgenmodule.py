
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from esp.middleware import ESPError
from esp.program.models import StudentRegistration
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
                    '06_username': 'Username',
                    '07_email': 'E-mail',
                    '08_accountdate': 'Created Date',
                    '09_first_regdate': 'Initial Registration Date',
                    '10_last_regdate': 'Most Recent Registration Date',
                    '11_cellphone': 'Mobile Phone',
                    '12_textmsg': 'Text Msg?',
                    '13_studentrep': 'Student Rep?',
                    '14_classhours': 'Num Class Hrs',
                    '15_gradyear': 'Grad Year',
                    '16_school': 'School',
                    '17_heard_about': 'Heard about Splash from',
                    '18_transportation': 'Plan to Get to Splash',
                    '19_dob': 'Date of Birth',
                    '21_tshirt_size': 'T-Shirt Size',
                    '22_gender': 'Gender',
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
        self.user = user
        self.program = program
        self.profile = self.user.getLastProfile()

    def get(self, attr):
        attr = attr.lstrip('0123456789_')
        #if attr = 'classapplication':

        result = getattr(self, 'get_' + attr)()
        if result is None or result == '':
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

    def get_username(self):
        return self.user.username

    def get_email(self):
        return self.user.email

    def get_accountdate(self):
        return self.user.date_joined.strftime("%m/%d/%Y")

    def get_regdate(self, ordering='start_date'):
        regs = StudentRegistration.valid_objects().filter(user=self.user, section__parent_class__parent_program=self.program, relationship__name='Enrolled')
        if regs.exists():
            return regs.order_by(ordering).values_list('start_date', flat=True)[0].strftime("%Y-%m-%d %H:%M:%S")

    def get_first_regdate(self):
        return self.get_regdate(ordering='start_date')

    def get_last_regdate(self):
        return self.get_regdate(ordering='-start_date')

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

    def get_tshirt_size(self):
        if self.profile.student_info:
            return self.profile.student_info.shirt_size
        elif self.profile.teacher_info:
            return self.profile.teacher_info.shirt_size
        else:
            return None

    def get_heard_about(self):
        if self.profile.student_info:
            return self.profile.student_info.heard_about

    def get_gradyear(self):
        if self.profile.student_info:
            return self.profile.student_info.graduation_year

    def get_transportation(self):
        if self.profile.student_info:
            return self.profile.student_info.transportation

    def get_dob(self):
        if self.profile.student_info:
            dob = self.profile.student_info.dob
            if dob:
                return '{:%Y-%m-%d}'.format(dob)

    def get_gender(self):
        if self.profile.student_info:
            return self.profile.student_info.gender

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
    split_by = forms.ChoiceField(choices=[('', '')] + attr_choices, required=False)
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

    @aux_call
    @needs_admin
    def generateList(self, request, tl, one, two, module, extra, prog, filterObj=None):
        """ Generate an HTML or CSV format user list using a query filter
            specified in request.GET or a separate argument. """

        if filterObj is None:
            if 'filterid' in request.GET:
                filterObj = PersistentQueryFilter.objects.get(id=request.GET['filterid'])
            else:
                raise ESPError('Could not determine the query filter ID.', log=False)

        if request.method == 'POST' and 'fields' in request.POST:
            #   If list information was submitted, continue to prepare a list
            #   Parse the contents of the form
            form = ListGenForm(request.POST)
            if form.is_valid():
                lists = []
                lists_indices = {}
                split_by = form.cleaned_data['split_by']

                labels_dict = UserAttributeGetter.getFunctions()
                fields = [labels_dict[f] for f in form.cleaned_data['fields']]
                #   If a split field is specified, make sure we fetch its data
                if split_by and labels_dict[split_by] not in fields:
                    fields.append(labels_dict[split_by])
                output_type = form.cleaned_data['output_type']

                users = list(ESPUser.objects.filter(filterObj.get_Q()).filter(is_active=True).distinct())
                users.sort()
                for u in users:
                    ua = UserAttributeGetter(u, self.program)
                    user_fields = [ua.get(x) for x in form.cleaned_data['fields']]
                    u.fields = user_fields
                    #   Add information for split lists if desired
                    if split_by:
                        if ua.get(split_by) not in lists_indices:
                            lists.append({'key': labels_dict[split_by], 'value': ua.get(split_by), 'users': []})
                            lists_indices[ua.get(split_by)] = len(lists) - 1
                        lists[lists_indices[ua.get(split_by)]]['users'].append(u)

                if split_by:
                    lists.sort(key=lambda x: x['value'])
                else:
                    lists.append({'users': users})

                if output_type == 'csv':
                    # properly speaking, this should be text/csv, but that
                    # causes Chrome to open in an external editor, which is
                    # annoying
                    mimetype = 'text/plain'
                elif output_type == 'html':
                    mimetype = 'text/html'
                else:
                    # WTF?
                    mimetype = 'text/html'
                return render_to_response(
                    self.baseDir()+('list_%s.html' % output_type),
                    request,
                    {'users': users, 'lists': lists, 'fields': fields, 'listdesc': filterObj.useful_name},
                    content_type=mimetype,
                )
            else:
                context = {
                    'form': form,
                    'filterid': filterObj.id,
                    'num_users': ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
                }
                return render_to_response(self.baseDir()+'options.html', request, context)
        else:
            #   Otherwise, show a blank form
            form = ListGenForm()
            context = {
                'form': form,
                'filterid': filterObj.id,
                'num_users': ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            }
            return render_to_response(self.baseDir()+'options.html', request, context)

    @main_call
    @needs_admin
    def selectList(self, request, tl, one, two, module, extra, prog):
        """ Select a group of users and generate a list of information
            about them using the generateList view above. """
        usc = UserSearchController()

        context = {}
        context['program'] = prog

        #   If list information was submitted, generate a query filter and
        #   show options for generating a user list
        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = {}
            for key in request.POST:
                data[key] = request.POST[key]
            filterObj = usc.filter_from_postdata(prog, data)

            #   Display list generation options
            form = ListGenForm()
            context.update({
                'form': form,
                'filterid': filterObj.id,
                'num_users': ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            })
            return render_to_response(self.baseDir()+'options.html', request, context)

        #   Otherwise, render a page that shows the list selection options
        context.update(usc.prepare_context(prog, target_path='/manage/%s/selectList' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    @aux_call
    @needs_admin
    def selectList_old(self, request, tl, one, two, module, extra, prog):
        """ Allow use of the "old style" user selector if that is desired for
            generating a list of users.     """

        from esp.users.views     import get_user_list
        from esp.users.models import PersistentQueryFilter

        if not 'filterid' in request.GET:
            filterObj, found = get_user_list(request, self.program.getLists(True))
        else:
            filterid  = request.GET['filterid']
            filterObj = PersistentQueryFilter.getFilterFromID(filterid, ESPUser)
            found     = True
        if not found:
            return filterObj

        return self.generateList(request, tl, one, two, module, extra, prog, filterObj=filterObj)

    class Meta:
        proxy = True
        app_label = 'modules'

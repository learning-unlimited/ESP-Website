
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
from django.conf import settings

from esp.middleware import ESPError
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.users.controllers.usersearch import UserSearchController
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.utils.web import render_to_response

from django.contrib.auth.models import Group
from django.db.models.query import Q


class NameTagModule(ProgramModuleObj):
    """ This module allows you to generate a bunch of IDs for everyone in the program. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Nametag Generation",
            "link_title": "Generate Nametags",
            "module_type": "manage",
            "seq": 100,
            "choosable": 1,
            }

    @main_call
    @needs_admin
    def selectidoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a page for admins to pick users for nametags """
        context = {'module': self}
        context['groups'] = Group.objects.all()
        usc = UserSearchController()
        context.update(usc.prepare_context(prog, target_path='/manage/%s/generatetags' % prog.url))

        return render_to_response(self.baseDir()+'selectoptions.html', request, context)

    def nametag_data(self, users_list, user_title):
        users = []
        users_list = [ user for user in users_list ]
        users_list = filter(lambda x: len(x.first_name+x.last_name), users_list)
        users_list.sort()

        for user in users_list:
            users.append({'title': user_title,
                          'name' : '%s %s' % (user.first_name, user.last_name),
                          'id'   : user.id,
                          'username': user.username})
        return users

    @aux_call
    @needs_admin
    def generatetags(self, request, tl, one, two, module, extra, prog):
        """ generate nametags """

        # Default to students
        if 'type' not in request.POST:
            raise ESPError("You need to select the TYPE of Name Tag to print. (students,teachers,etc)", log=False)
        idtype = request.POST['type']

        users = []

        user_title = idtype

        if idtype == 'aul':
            user_title = request.POST['blanktitle']
            data = {}
            for key in request.POST:
                data[key] = request.POST[key]
            usc = UserSearchController()
            filterObj = usc.filter_from_postdata(prog, data)
            users = self.nametag_data(ESPUser.objects.filter(filterObj.get_Q()).distinct(), user_title)

        elif idtype == 'students':
            user_title = "Student"
            student_dict = self.program.students(QObjects = True)
            if 'classreg' in student_dict:
                students = ESPUser.objects.filter(student_dict['classreg']).distinct()
            else:
                students = ESPUser.objects.filter(student_dict['confirmed']).distinct()

            users = self.nametag_data(students, user_title)

        elif idtype == 'teacher':
            user_title = "Teacher"
            teacher_dict = self.program.teachers(QObjects=True)
            teachers = ESPUser.objects.filter(teacher_dict['class_approved']).distinct()

            users = self.nametag_data(teachers, user_title)

        elif idtype == 'other':
            user_title = request.POST['blanktitle']
            if request.POST['group'] == '':
                raise ESPError("You need to select a group", log=False)
            group = request.POST['group']
            user_Q = Q(groups=group)
            users_list = ESPUser.objects.filter(user_Q).distinct()

            users = self.nametag_data(users_list, user_title)

        elif idtype == 'volunteers':
            user_title = "Volunteer"
            volunteer_dict = self.program.volunteers(QObjects=True)
            volunteers = ESPUser.objects.filter(volunteer_dict['volunteer_all']).distinct()

            users = self.nametag_data(volunteers, user_title)

        elif idtype == 'misc':
            users = []
            misc = request.POST['misc_info']
            for user in misc.split("\n"):
                arruser = user.split(",", 1)

                if len(arruser) >= 2:
                    user_title = arruser[1].strip()
                    users.append({'title': user_title,
                                  'name' : arruser[0].strip(),
                                  'id'   : ''})


        elif idtype == 'blank':
            users = []
            user_title = request.POST['blanktitle']
            for i in range(int(request.POST['number'])):
                users.append({'title': user_title,
                              'name' : '',
                              'id'   : ''})

        context = {'module': self,
                   'programname': request.POST['progname']
                   }


        numperpage = 6


        expanded = [[] for i in range(numperpage)]

        for i in range(len(users)):
            expanded[(i*numperpage)/len(users)].append(users[i])

        users = []

        for i in range(len(expanded[0])):
            for j in range(len(expanded)):
                if len(expanded[j]) <= i:
                    users.append({'title': user_title,
                                  'name' : '',
                                  'id'   : ''})
                else:
                    users.append(expanded[j][i])

        user_backs = [None]*len(users)
        for j in range(len(users)):
            if j % 2 == 0:
                user_backs[j+1] = users[j]
            else:
                user_backs[j-1] = users[j]

        users_and_backs = []
        for j in range(len(users)/6):
            users_and_backs.append([users[j*6:(j+1)*6], user_backs[j*6:(j+1)*6]])

        context['barcodes'] = True if 'barcodes' in request.POST else False
        context['users_and_backs'] = users_and_backs
        context['group_name'] = Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)
        context['phone_number'] = Tag.getTag('group_phone_number')

        return render_to_response(self.baseDir()+'ids.html', request, context)


    class Meta:
        proxy = True
        app_label = 'modules'


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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models import ESPUser, User
from django.db.models.query import Q
from esp.users.views  import get_user_list
from esp.middleware import ESPError
from esp.web.util.latex import render_to_latex
from esp.tagdict.models import Tag
from django.conf import settings
class NameTagModule(ProgramModuleObj):
    """ This module allows you to generate a bunch of IDs for everyone in the program. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Nametag Generation",
            "link_title": "Generate Nametags",
            "module_type": "manage",
            "seq": 100
            }

    @main_call
    @needs_admin
    def selectidoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {'module': self}

        return render_to_response(self.baseDir()+'selectoptions.html', request, context)

    @aux_call
    @needs_admin
    def generatestickers(self, request, tl, one, two, module, extra, prog):
        timeslots = prog.getTimeSlots()
        students = prog.students()['confirmed']
        context = {'timeslots': timeslots, 'students': students}
        if request.GET.has_key("format"):
            format = request.GET["format"]
        else:
            format = "pdf"
            
        zipped_list = []

        students = list(students)
        
        while students != []:
            zipped_list.append(students[:3])
            students = students[3:]

        context['zipped_list'] = zipped_list
            
        return render_to_latex(self.baseDir()+'stickers.tex', context, format)

    @aux_call
    @needs_admin
    def generatetags(self, request, tl, one, two, module, extra, prog):
        """ generate nametags """

        # Default to students
        if 'type' not in request.POST:
            raise ESPError(log=False), "You need to select the TYPE of Name Tag to print. (students,teachers,etc)"
        idtype = request.POST['type']

        users = []

        user_title = idtype
        
        if idtype == 'students':
            student_dict = self.program.students(QObjects = True)
            if 'classreg' in student_dict:
                students = ESPUser.objects.filter(student_dict['classreg']).distinct()
            else:
                students = ESPUser.objects.filter(student_dict['confirmed']).distinct()

            students = filter(lambda x: len(x.first_name+x.last_name), students)
            students.sort()

            user_title = "Student"
            for student in students:
                users.append({'title': user_title,
                              'name' : '%s %s' % (student.first_name, student.last_name),
                              'id'   : student.id,
                              'username': student.username})
                
        elif idtype == 'teacher':
            teachers = []
            teacher_dict = self.program.teachers(QObjects=True)
            teachers = ESPUser.objects.filter(teacher_dict['class_approved']).distinct()
#            teachers =ESPUser.objects.filter(teacher_dict['teacher_profile'] | teacher_dict['class_rejected']).distinct()

	    teachers = [ ESPUser(teacher) for teacher in teachers ]
            teachers = filter(lambda x: len(x.first_name+x.last_name), teachers)
            teachers.sort()

            user_title = "Teacher"
            for teacher in teachers:
                users.append({'title': user_title,
                              'name' : '%s %s' % (teacher.first_name, teacher.last_name),
                              'id'   : teacher.id,
                              'username': teacher.username})

        elif idtype == 'volunteers':
            users = []
            volunteers = request.POST['volunteers']
            for user in volunteers.split("\n"):
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

        context['users'] = users
        context['group_name'] = Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)
        context['phone_number'] = Tag.getTag('group_phone_number')
            
        return render_to_response(self.baseDir()+'ids.html', request, context)
        


    class Meta:
        abstract = True


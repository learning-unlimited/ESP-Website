
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, CoreModule
from esp.middleware.esperrormiddleware import ESPError
from esp.program.modules import module_ext
from esp.program.modules.forms.junction_teacher_review import JunctionTeacherReview
from esp.users.models import ESPUser, UserBit
from esp.web.util        import render_to_response
from esp.program.models import Class, JunctionStudentApp, JunctionAppReview
from django.contrib.auth.decorators import login_required
from esp.datatree.models import DataTree
from django.http import HttpResponseRedirect

__all__ = ['TeacherReviewApps']

class TeacherReviewApps(ProgramModuleObj, CoreModule):

    @meets_deadline()
    @needs_teacher
    def review_students(self, request, tl, one, two, module, extra, prog):
        try:
            cls = Class.objects.get(id = extra)
        except Class.DoesNotExist:
            raise ESPError(False), 'Cannot find class.'

        if not self.user.canEdit(cls):
            raise ESPError(False), 'You cannot edit class "%s"' % cls

        students = cls.students()

        for student in students:
            student.added_class = student.userbit_set.filter(qsc = cls.anchor)[0].startdate
            try:
                student.app = student.junctionstudentapp_set.get(program = self.program)
            except:
                student.app = None

            reviews = student.junctionappreview_set.filter(cls = cls)

            if len(reviews) > 0:
                student.app_reviewed = reviews[0]
            else:
                student.app_reviewed = None

        students.sort(lambda x,y: cmp(x.added_class,y.added_class))

        return render_to_response(self.baseDir()+'roster.html',
                                  request,
                                  (prog, tl),
                                  {'class': cls,
                                   'students':students})

        
    
    @meets_deadline()
    @needs_teacher
    def review_student(self, request, tl, one, two, module, extra, prog):

        reg_node = request.get_node('V/Flags/Registration/Preliminary')

        try:
            cls = Class.objects.get(id = extra)
        except Class.DoesNotExist:
            raise ESPError(False), 'Cannot find class.'

        if not self.user.canEdit(cls):
            raise ESPError(False), 'You cannot edit class "%s"' % cls

        student = request.GET.get('student',None)
        if not student:
            student = request.POST.get('student','')

        try:
            student = ESPUser(ESPUser.objects.get(id = student))
        except ESPUser.DoesNotExist:
            raise ESPError(False), 'Cannot find student, %s' % student

        if not UserBit.objects.UserHasPerms(user = student,
                                            qsc  = cls.anchor,
                                            verb = reg_node):
            raise ESPError(False), 'Student not a student of this class.'

        try:
            student.app = student.junctionstudentapp_set.get(program = self.program)
        except:
            student.app = None
            raise ESPError(False), 'Error: Student did not apply. Student is automatically rejected.'

        student.added_class = student.userbit_set.filter(qsc = cls.anchor)[0].startdate

        reviews = student.junctionappreview_set.filter(cls = cls)

        if len(reviews) > 0:
            student.app_review = reviews[0]
        else:
            student.app_review = JunctionAppReview(cls=cls,
                                                   student=student,
                                                   junctionapp = student.app)


        initial = {'rejected': student.app.rejected,
                   'score':    student.app_review.score}

        if request.method == 'POST':
            form = JunctionTeacherReview(request.POST, initial=initial)

            if form.is_valid():
                student.app.rejected = form.clean_data['rejected']
                student.app.save()
                student.app_review.score = form.clean_data['score']
                student.app_review.save()
                return HttpResponseRedirect('/teach/%s/review_students/%s/' %\
                                            (self.program.getUrlBase(),cls.id))
        else:
            form = JunctionTeacherReview(initial=initial)

        return render_to_response(self.baseDir()+'review.html',
                                  request,
                                  (prog, tl),
                                  {'class': cls,
                                   'student':student,
                                   'form': form})

    def prepare(self, context):
        context['classes'] = self.user.getTaughtClasses().filter(parent_program = self.program)
        return context

    def isStep(self):
        return True


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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, CoreModule, main_call, aux_call
from esp.middleware.esperrormiddleware import ESPError
from esp.program.modules import module_ext
from esp.program.modules.forms.junction_teacher_review import JunctionTeacherReview
from esp.users.models import ESPUser, UserBit, User
from esp.web.util        import render_to_response
from esp.program.models import ClassSubject, StudentApplication, StudentAppQuestion, StudentAppResponse, StudentAppReview
from django.contrib.auth.decorators import login_required
from esp.datatree.models import *
from django.http import HttpResponseRedirect

__all__ = ['TeacherReviewApps']

class TeacherReviewApps(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Junction Application Review",
            "module_type": "teach",
            "seq": 1000,
            "main_call": "teacherreviewapp"
            }

    @aux_call
    @meets_deadline("/AppReview")
    @needs_teacher
    def review_students(self, request, tl, one, two, module, extra, prog):
        try:
            cls = ClassSubject.objects.get(id = extra)
        except ClassSubject.DoesNotExist:
            raise ESPError(False), 'Cannot find class.'

        if not self.user.canEdit(cls):
            raise ESPError(False), 'You cannot edit class "%s"' % cls

        students = cls.students()

        for student in students:
            student.added_class = student.userbit_set.filter(qsc__parent = cls.anchor)[0].startdate
            try:
                student.app = student.studentapplication_set.get(program = self.program)
            except:
                student.app = None

            if student.app:
                reviews = student.app.reviews.all()
            else:
                reviews = []

            if len(reviews) > 0:
                student.app_reviewed = reviews[0]
            else:
                student.app_reviewed = None

        students = list(students)
        students.sort(lambda x,y: cmp(x.added_class,y.added_class))

        return render_to_response(self.baseDir()+'roster.html',
                                  request,
                                  (prog, tl),
                                  {'class': cls,
                                   'students':students})

    @aux_call
    @meets_deadline()
    @needs_teacher
    def app_questions(self, request, tl, one, two, module, extra, prog):
        """ Edit the subject-specific questions that students will respond to on
        their applications. """
        subjects = self.user.getTaughtClasses(prog)
        clrmi = module_ext.ClassRegModuleInfo.objects.get(module__program=self.program)
        question_list = []

        #   Provide forms to modify existing questions, and also blank forms for new questions
        #   up to the maximum number specified in ClassRegModuleInfo.
        for s in subjects:
            existing_questions = StudentAppQuestion.objects.filter(subject=s)
            question_list += list(existing_questions)
            if existing_questions.count() < clrmi.num_teacher_questions:
                for i in range(0, clrmi.num_teacher_questions - existing_questions.count()):
                    q = StudentAppQuestion(subject=s)
                    q.save()
                    question_list.append(q)
        
        if request.method == 'POST':
            data = request.POST.copy()
            for q in question_list:
                form = q.get_form(data)
                if form.is_valid():
                    q.update(form)
            return self.goToCore(tl)
            
        context = {'clrmi': clrmi, 'prog': prog, 'questions': question_list}
        return render_to_response(self.baseDir()+'questions.html', request, (prog, tl), context)

    @aux_call
    @meets_deadline("/AppReview")
    @needs_teacher
    def review_student(self, request, tl, one, two, module, extra, prog):
        reg_node = request.get_node('V/Flags/Registration/Applied')

        try:
            cls = ClassSubject.objects.get(id = extra)
        except ClassSubject.DoesNotExist:
            raise ESPError(False), 'Cannot find class.'

        if not self.user.canEdit(cls):
            raise ESPError(False), 'You cannot edit class "%s"' % cls

        student = request.GET.get('student',None)
        if not student:
            student = request.POST.get('student','')

        try:
            student = ESPUser(User.objects.get(id = student))
        except ESPUser.DoesNotExist:
            raise ESPError(False), 'Cannot find student, %s' % student

        section_anchors = [s.anchor for s in cls.sections.all()]
        not_registered = True
        for s in section_anchors:
            if UserBit.objects.UserHasPerms(user=student, qsc=s, verb=reg_node):
                not_registered = False
        if not_registered:
            raise ESPError(False), 'Student not a student of this class.'

        try:
            student.app = student.studentapplication_set.get(program = self.program)
        except:
            student.app = None
            raise ESPError(False), 'Error: Student did not apply. Student is automatically rejected.'

        student.added_class = student.userbit_set.filter(qsc__parent = cls.anchor)[0].startdate

        reviews = student.app.reviews.all()
        if reviews.filter(reviewer=self.user).count() > 0:
            this_review = reviews.filter(reviewer=self.user).order_by('id')[0]
        else:
            this_review = StudentAppReview(reviewer=self.user)
            this_review.save()
            student.app.reviews.add(this_review)

        if request.method == 'POST':
            data = request.POST.copy()
            form = this_review.get_form(data)
            if form.is_valid():
                form.target.update(form)
        else:
            form = this_review.get_form()

        return render_to_response(self.baseDir()+'review.html',
                                  request,
                                  (prog, tl),
                                  {'class': cls,
                                  'program': prog,
                                   'student':student,
                                   'form': form})

    def prepare(self, context):
        context['classes'] = self.user.getTaughtClasses().filter(parent_program = self.program)
        return context

    def isStep(self):
        return True

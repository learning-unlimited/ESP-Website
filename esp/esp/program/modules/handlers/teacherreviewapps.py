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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.middleware.esperrormiddleware import ESPError
from esp.program.modules import module_ext
from esp.program.modules.forms.junction_teacher_review import JunctionTeacherReview
from esp.users.models import ESPUser, UserBit, User
from esp.web.util        import render_to_response
from esp.program.models import ClassSubject, StudentApplication, StudentAppQuestion, StudentAppResponse, StudentAppReview
from django.contrib.auth.decorators import login_required
from esp.datatree.models import *
from django.http import HttpResponseRedirect
from datetime import datetime

__all__ = ['TeacherReviewApps']

class TeacherReviewApps(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Application Reviews for Teachers",
            "link_title": "Review Student Applications",
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

        #   Fetch any student even remotely related to the class.
        students_dict = cls.students_dict()
        students = []
        for key in students_dict:
            students += students_dict[key]

        for student in students:
            now = datetime.now()
            student.added_class = student.userbit_set.filter(qsc__parent = cls.anchor)[0].startdate
            student.added_userbits = student.userbit_set.filter(startdate__lte=now, enddate__gte=now).filter(qsc__parent = cls.anchor).order_by('-startdate').distinct()

            try:
                student.app = student.studentapplication_set.get(program = self.program)
            except:
                student.app = None

            if student.app:
                reviews = student.app.reviews.all().filter(reviewer=self.user, score__isnull=False)
                questions = student.app.questions.all().filter(subject=cls)
            else:
                reviews = []
                questions = []

            if len(reviews) > 0:
                student.app_reviewed = reviews[0]
            else:
                student.app_reviewed = None
            
            student.app_completed = False
            for i in questions:
                for j in i.studentappresponse_set.all():
                    if j.complete:
                        student.app_completed = True

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
                    question_list.append(q)
        
        #   Initialize forms with nonstandard prefixes if they correspond to questions
        #   that have not yet been saved.
        form_list = []
        i = 1
        for q in question_list:
            if not (hasattr(q, 'id') and q.id):
                form = q.get_form(form_prefix='question_new_%d' % i)
            else:
                form = q.get_form()
            form.app_question = q
            form_list.append(form)
            i += 1
        
        if request.method == 'POST':
            data = request.POST
            for f in form_list:
                #   Reinitialize the form with a bound one having the same prefix.
                q = f.app_question
                form = f.app_question.get_form(data, form_prefix=f.prefix)
                
                #   If the form is valid, save the question.  If not, delete it.
                if form.is_valid():
                    q.update(form)
                    q.save()
                else:
                    if hasattr(q, 'id') and q.id:
                        q.delete()

            return self.goToCore(tl)
            
        context = {'clrmi': clrmi, 'prog': prog, 'forms': form_list}
        return render_to_response(self.baseDir()+'questions.html', request, (prog, tl), context)

    @aux_call
    @meets_deadline("/AppReview")
    @needs_teacher
    def review_student(self, request, tl, one, two, module, extra, prog):
        scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')
        reg_nodes = scrmi.reg_verbs()

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

        not_registered = (student.userbit_set.filter(qsc__parent=cls.anchor, verb__in=reg_nodes).count() == 0)
        if not_registered:
            raise ESPError(False), 'Student not a student of this class.'

        try:
            student.app = student.studentapplication_set.get(program = self.program)
        except:
            student.app = None
            raise ESPError(False), 'Error: Student did not start an application.'

        student.added_class = student.userbit_set.filter(qsc__parent = cls.anchor)[0].startdate

        teacher_reviews = student.app.reviews.all().filter(reviewer=self.user)
        if teacher_reviews.count() > 0:
            this_review = teacher_reviews.order_by('id')[0]
        else:
            this_review = StudentAppReview(reviewer=self.user)
            this_review.save()
            student.app.reviews.add(this_review)

        if request.method == 'POST':
            form = this_review.get_form(request.POST)
            if form.is_valid():
                form.target.update(form)
        else:
            form = this_review.get_form()

        return render_to_response(self.baseDir()+'review.html',
                                  request,
                                  (prog, tl),
                                  {'class': cls,
                                   'reviews': teacher_reviews,
                                  'program': prog,
                                   'student':student,
                                   'form': form})

    def prepare(self, context):
        clrmi = module_ext.ClassRegModuleInfo.objects.get(module__program=self.program)
        context['num_teacher_questions'] = clrmi.num_teacher_questions;
        context['classes'] = self.user.getTaughtClasses().filter(parent_program = self.program)
        return context

    def isStep(self):
        return True


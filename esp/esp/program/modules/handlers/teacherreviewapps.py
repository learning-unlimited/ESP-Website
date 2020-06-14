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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.middleware.esperrormiddleware import ESPError
from esp.program.modules import module_ext
from esp.program.modules.forms.junction_teacher_review import JunctionTeacherReview
from esp.users.models import ESPUser, User
from esp.utils.web import render_to_response
from esp.program.models import ClassSubject, StudentApplication, StudentAppQuestion, StudentAppResponse, StudentAppReview, StudentRegistration
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from datetime import datetime
from django.views.decorators.cache import never_cache
from esp.middleware.threadlocalrequest import get_current_request

__all__ = ['TeacherReviewApps']

class TeacherReviewApps(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Application Reviews for Teachers",
            "link_title": "Review Student Applications",
            "module_type": "teach",
            "seq": 1000,
            "inline_template": "teacherreviewapp.html",
            "choosable": 0,
            }

    @aux_call
    @needs_teacher
    @meets_deadline("/AppReview")
    @never_cache
    def review_students(self, request, tl, one, two, module, extra, prog):
        try:
            cls = ClassSubject.objects.get(id = extra)
        except ClassSubject.DoesNotExist:
            raise ESPError('Cannot find class.', log=False)

        if not request.user.canEdit(cls):
            raise ESPError('You cannot edit class "%s"' % cls, log=False)

        #   Fetch any student even remotely related to the class.
        students_dict = cls.students_dict()
        students = []
        for key in students_dict:
            students += students_dict[key]

        for student in students:
            now = datetime.now()
            student.added_class = StudentRegistration.valid_objects().filter(section__parent_class = cls, user = student)[0].start_date
            try:
                student.app = student.studentapplication_set.get(program = self.program)
            except:
                student.app = None

            if student.app:
                reviews = student.app.reviews.all().filter(reviewer=request.user, score__isnull=False)
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

        if 'prev' in request.GET:
            prev_id = int(request.GET.get('prev'))
            prev = students[0]
            current = None
            for current in students[1:]:
                if prev.id == prev_id and current.app_completed:
                    from django.shortcuts import redirect
                    url = "/%s/%s/%s/review_student/%s/?student=%s" % (tl, one, two, extra, current.id)
                    return redirect(url)
                if prev.id != prev_id:
                    prev = current


        return render_to_response(self.baseDir()+'roster.html',
                                  request,
                                  {'class': cls,
                                   'students':students})

    @aux_call
    @needs_teacher
    @meets_deadline()
    def app_questions(self, request, tl, one, two, module, extra, prog):
        """ Edit the subject-specific questions that students will respond to on
        their applications. """
        subjects = request.user.getTaughtClasses(prog)
        clrmi = module_ext.ClassRegModuleInfo.objects.get(program=self.program)
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
        return render_to_response(self.baseDir()+'questions.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline("/AppReview")
    def review_student(self, request, tl, one, two, module, extra, prog):
        scrmi = prog.studentclassregmoduleinfo
        reg_nodes = scrmi.reg_verbs()

        try:
            cls = ClassSubject.objects.get(id = extra)
        except ClassSubject.DoesNotExist:
            raise ESPError('Cannot find class.', log=False)

        if not request.user.canEdit(cls):
            raise ESPError('You cannot edit class "%s"' % cls, log=False)

        student = request.GET.get('student',None)
        if not student:
            student = request.POST.get('student','')

        try:
            student = ESPUser.objects.get(id = int(student))
        except ESPUser.DoesNotExist:
            raise ESPError('Cannot find student, %s' % student, log=False)

        not_registered = not StudentRegistration.valid_objects().filter(section__parent_class = cls, user = student).exists()
        if not_registered:
            raise ESPError('Student not a student of this class.', log=False)

        try:
            student.app = student.studentapplication_set.get(program = self.program)
        except:
            student.app = None
            raise ESPError('Error: Student did not start an application.', log=False)

        student.added_class = StudentRegistration.valid_objects().filter(section__parent_class = cls, user = student)[0].start_date

        teacher_reviews = student.app.reviews.all().filter(reviewer=request.user)
        if teacher_reviews.count() > 0:
            this_review = teacher_reviews.order_by('id')[0]
        else:
            this_review = StudentAppReview(reviewer=request.user)
            this_review.save()
            student.app.reviews.add(this_review)

        if request.method == 'POST':
            form = this_review.get_form(request.POST)
            if form.is_valid():
                form.target.update(form)
                if 'submit_next' in request.POST or 'submit_return' in request.POST:
                    url = '/%s/%s/%s/review_students/%s/' % (tl, one, two, extra)
                    if 'submit_next' in request.POST:
                        url += '?prev=%s' % student.id
                    from django.shortcuts import redirect
                    return redirect(url) # self.review_students(request, tl, one, two, module, extra, prog)


        else:
            form = this_review.get_form()

        return render_to_response(self.baseDir()+'review.html',
                                  request,
                                  {'class': cls,
                                   'reviews': teacher_reviews,
                                  'program': prog,
                                   'student':student,
                                   'form': form})

    def prepare(self, context):
        clrmi = module_ext.ClassRegModuleInfo.objects.get(program=self.program)
        context['num_teacher_questions'] = clrmi.num_teacher_questions;
        context['classes'] = get_current_request().user.getTaughtClasses().filter(parent_program = self.program)
        return context

    def isStep(self):
        return True


    class Meta:
        proxy = True
        app_label = 'modules'

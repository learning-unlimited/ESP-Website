
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
from esp.program.modules import module_ext
from esp.utils.web import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser
from django.db.models.query       import Q
from django.template.loader import get_template
from esp.program.models  import StudentApplication
from django              import forms
from esp.middleware.threadlocalrequest import get_current_request

# student class picker module
class StudentJunctionAppModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Application",
            "link_title": "Extra Application Info",
            "module_type": "learn",
            "seq": 10000,
            "required": True,
            "choosable": 2,
            }

    def students(self, QObject = False):
        Q_students = Q(studentapplication__program = self.program)

        Q_students_complete = Q(studentapplication__done = True)

        if QObject:
            return {'studentapps_complete': Q_students & Q_students_complete,
                    'studentapps':          Q_students}
        else:
            return {'studentapps_complete': ESPUser.objects.filter(Q_students & Q_students_complete),
                    'studentapps':          ESPUser.objects.filter(Q_students)}

    def studentDesc(self):
        return {'studentapps_complete': """Students who have completed the student application""",
                'studentapps':          """Students who have started the student application"""}

    def isCompleted(self):
        """ This step is completed if the student has marked their application as complete or answered questions for
        all of their classes.  I know this is slow sometimes.  -Michael P"""

        app = get_current_request().user.getApplication(self.program)

        #   Check if the application is empty or marked as completed.
        if app.done:
            return True
        app.set_questions()
        if app.questions.all().count() == 0:
            return True

        #   Code below here may be unnecessary; it's just to save students the trouble
        #   of clicking through to mark their application complete before they can confirm.

        #   Get the student's responses to application questions.
        responses = app.responses.all()
        response_question_ids = [x.question.id for x in responses]
        response_dict = {}
        for i in range(len(responses)):
            response_dict[response_question_ids[i]] = responses[i]

        #   Check that they responded to everything.
        classes = get_current_request().user.getAppliedClasses(self.program)
        for cls in classes:
            for i in [x['id'] for x in cls.studentappquestion_set.all().values('id')]:
                if i not in response_question_ids:
                    return False
                elif (not response_dict[i].complete) and len(response_dict[i].response) == 0:
                    return False
        return True

    def deadline_met(self):
        return super(StudentJunctionAppModule, self).deadline_met('/Applications')

    @main_call
    @needs_student
    @meets_deadline('/Applications')
    def application(self,request, tl, one, two, module, extra, prog):
        app = request.user.getApplication(self.program)
        app.set_questions()
        form = None
        if request.method == 'POST':
            data = request.POST.copy()
            forms = app.get_forms(data)
            for form in forms:
                if form.is_valid():
                    form.target.update(form)
            if request.POST['submitform'].lower() == 'complete':
                app.done = True
            if request.POST['submitform'].lower() == 'mark as unfinished':
                app.done = False
            app.save()
            return self.goToCore(tl)
        else:
            forms = app.get_forms()

        return render_to_response(self.baseDir()+'application.html', request, {'forms': forms, 'app': app})

    def isStep(self):
        return self.program.isUsingStudentApps()

    class Meta:
        proxy = True
        app_label = 'modules'


__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.web.util        import render_to_response
from esp.utils.decorators import json_response
from esp.application.models import StudentProgramApp, StudentClassApp, FormstackStudentProgramApp

class AdmissionsDashboard(ProgramModuleObj):
    """
    A dashboard for Junction core teachers to review applications for their class.

    Not to be confused with TeacherReviewApps, the app questions module.
    """

    @classmethod
    def module_properties(cls):
        return [{
                "admin_title": "Teacher Admissions Dashboard",
                "link_title": "Admissions Dashboard",
                "module_type": "teach",
                },
                {
                "admin_title": "Admin Admissions Dashboard",
                "link_title": "Admissions Dashboard",
                "module_type": "manage",
                }]

    @main_call
    def admissions(self, request, tl, one, two, module, extra, prog):
        if request.user.isAdmin(prog):
            classes = prog.classes()
        else:
            classes = request.user.getTaughtClassesFromProgram(prog)
        admin_status_choices = StudentProgramApp._meta.get_field('admin_status').choices
        teacher_rating_choices = StudentClassApp._meta.get_field('teacher_rating').choices
        admission_status_choices = StudentClassApp._meta.get_field('admission_status').choices
        return render_to_response(self.baseDir() + 'admissions.html',
                                  request,
                                  (prog, tl),
                                  {'classes': classes,
                                   'admin_status_choices': admin_status_choices,
                                   'teacher_rating_choices': teacher_rating_choices,
                                   'admission_status_choices': admission_status_choices})

    @aux_call
    @needs_teacher
    @json_response(None)
    def apps(self, request, tl, one, two, module, extra, prog):
        if prog.getModuleExtension('FormstackAppSettings'):
            FormstackStudentProgramApp.objects.fetch(prog) # keep DB ~up to date
        classapps = StudentClassApp.objects.filter(app__program=prog)
        if not request.user.isAdmin(prog):
            classes = request.user.getTaughtClassesFromProgram(prog)
            classapps = classapps.filter(subject__in=classes)
        if extra:
            classapps = classapps.filter(subject__id=extra)

        results = []
        for classapp in classapps:
            result = {}
            result['id'] = classapp.id
            result['user'] = {'id': classapp.app.user.id,
                              'name': classapp.app.user.name()}
            result['subject'] = {'id': classapp.subject.id,
                                 'title': classapp.subject.title()}
            result['teacher_rating'] = classapp.teacher_rating
            result['teacher_ranking'] = classapp.teacher_ranking
            result['teacher_comment'] = classapp.teacher_comment
            result['student_preference'] = classapp.student_preference
            if tl == 'manage' and request.user.isAdmin(prog):
                result['admin_status'] = classapp.app.admin_status
                result['admin_comment'] = classapp.app.admin_comment
                result['admission_status'] = classapp.admission_status
            results.append(result)
        return {'apps': results}

    @aux_call
    @needs_teacher
    @json_response(None)
    def app(self, request, tl, one, two, module, extra, prog):
        try:
            classapp = StudentClassApp.objects.get(id=extra)
        except StudentClassApp.DoesNotExist:
            return # XXX: more useful error here
        if not (request.user.isAdmin(prog) or classapp.subject in request.user.getTaughtClassesFromProgram(prog)):
            return
        content = classapp.get_teacher_view(prog)
        return {'app': content}

    @aux_call
    @needs_teacher
    @json_response(None)
    def update_app(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            try:
                classapp = StudentClassApp.objects.get(id=extra)
            except StudentClassApp.DoesNotExist:
                return # XXX: more useful error here
            if not (request.user.isAdmin(prog) or classapp.subject in request.user.getTaughtClassesFromProgram(prog)):
                return
            post = request.POST
            if 'teacher_rating' in post:
                classapp.teacher_rating = post['teacher_rating'] or None
            if 'teacher_ranking' in post:
                classapp.teacher_ranking = post['teacher_ranking'] or None
            if 'teacher_comment' in post:
                classapp.teacher_comment = post['teacher_comment']
            classapp.save()

            if request.user.isAdmin():
                if 'admin_status' in post:
                    classapp.app.admin_status = post['admin_status']
                if 'admin_comment' in post:
                    classapp.app.admin_comment = post['admin_comment']
                classapp.app.save()

                if 'admission_status' in post:
                    admission_status = int(post['admission_status'])
                    if admission_status == StudentClassApp.ADMITTED:
                        classapp.admit()
                    elif admission_status == StudentClassApp.UNASSIGNED:
                        classapp.unadmit()
                    elif admission_status == StudentClassApp.WAITLIST:
                        classapp.waitlist()

            return {'success': 1}

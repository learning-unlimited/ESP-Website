

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
from esp.users.models import ESPUser
from esp.utils.web import render_to_response
from esp.program.models import ClassSubject, StudentApplication, StudentAppReview, StudentRegistration, RegistrationType
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.db.models.query import Q

__all__ = ['AdminReviewApps']

class AdminReviewApps(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Application Review for Admin",
            "link_title": "Application Review for Admin",
            "module_type": "manage",
            "seq": 1000,
            "choosable": 0,
            }

    def students(self, QObject=False):
        Q_accepted = Q(studentregistration__relationship__name='Accepted', studentregistration__section__parent_class__parent_program=self.program)

        if QObject:
            return {'app_accepted_to_one_program': Q_accepted}
        else:
            return {'app_accepted_to_one_program': ESPUser.objects.filter(Q_accepted).distinct()}

    def studentDesc(self):
        return {'app_accepted_to_one_program': """Students who are accepted to at least one class"""}

    @main_call
    @needs_admin
    def review_students(self, request, tl, one, two, module, extra, prog):
        """ Show a roster of the students in the class, allowing the administrators
        to accept students into the program based on the teachers' reviews and the
        students' applications. """

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

        students = filter(lambda x: x.studentapplication_set.filter(program=self.program).count() > 0, students)

        for student in students:
            student.added_class = student.studentregistration_set.filter(section__parent_class=cls)[0].start_date
            try:
                student.app = student.studentapplication_set.get(program = self.program)
            except:
                student.app = None

            if student.app:
                reviews = student.app.reviews.all()
            else:
                reviews = []

            if StudentRegistration.valid_objects().filter(user=student, section__parent_class=cls, relationship__name='Accepted').count() > 0:
                student.status = 'Accepted'
            else:
                student.status = 'Not accepted'

        students = list(students)
        students.sort(key=lambda x: x.last_name)

        return render_to_response(self.baseDir()+'roster.html',
                                  request,
                                  {'class': cls,
                                   'students':students, 'program': prog})

    @aux_call
    @needs_admin
    def accept_student(self, request, tl, one, two, module, extra, prog):
        """ Accept a student into a class. """

        try:
            cls = ClassSubject.objects.get(id = request.GET.get('cls',''))
            student = ESPUser.objects.get(id = request.GET.get('student',''))
        except:
            raise ESPError('Student or class not found.', log=False)

        #   Note: no support for multi-section classes.
        sec = cls.get_sections()[0]
        (rtype, created) = RegistrationType.objects.get_or_create(name='Accepted')
        StudentRegistration.objects.get_or_create(user=student, section=sec, relationship=rtype)
        return self.review_students(request, tl, one, two, module, extra, prog)

    @aux_call
    @needs_admin
    def reject_student(self, request, tl, one, two, module, extra, prog):
        """ Reject a student from a class (does not affect their
        registration). """

        try:
            cls = ClassSubject.objects.get(id = request.GET.get('cls',''))
            student = ESPUser.objects.get(id = request.GET.get('student',''))
        except:
            raise ESPError('Student or class not found.', log=False)

        #   Note: no support for multi-section classes.
        sec = cls.get_sections()[0]
        (rtype, created) = RegistrationType.objects.get_or_create(name='Accepted')
        for reg in StudentRegistration.objects.filter(user=student, section=sec, relationship=rtype):
            reg.expire()

        return self.review_students(request, tl, one, two, module, extra, prog)

    @aux_call
    @needs_admin
    def view_app(self, request, tl, one, two, module, extra, prog):
        scrmi = prog.studentclassregmoduleinfo
        reg_nodes = scrmi.reg_verbs()

        try:
            cls = ClassSubject.objects.get(id = extra)
            section = cls.default_section()
        except ClassSubject.DoesNotExist:
            raise ESPError('Cannot find class.', log=False)

        student = request.GET.get('student',None)
        if not student:
            student = request.POST.get('student','')

        try:
            student = ESPUser.objects.get(id = student)
        except ESPUser.DoesNotExist:
            raise ESPError('Cannot find student, %s' % student, log=False)

        if student.studentregistration_set.filter(section__parent_class=cls).count() == 0:
            raise ESPError('Student not a student of this class.', log=False)

        try:
            student.app = student.studentapplication_set.get(program = self.program)
        except:
            student.app = None
            assert False, student.studentapplication_set.all()[0].__dict__
            raise ESPError('Error: Student did not apply. Student is automatically rejected.', log=False)

        return render_to_response(self.baseDir()+'app_popup.html', request, {'class': cls, 'student': student, 'program': prog})

    def prepare(self, context):
        """ Sets the 'classes' template variable to contain the list of classes that the current user is teaching """
        context['classes_to_review'] = self.program.classes()
        return context

    def isStep(self):
        return True

    def get_msg_vars(self, user, key):
        if key == 'schedule_app':
            return AdminReviewApps.getSchedule(self.program, user)

        return None

    @staticmethod
    def getSchedule(program, student):

        schedule = u"""
Student schedule for %s:

 Time               | Class                   | Room""" % student.name()


        regs = StudentRegistration.valid_objects().filter(user=student, section__parent_class__parent_program=program, relationship__name='Accepted')
        classes = [x.section.parent_class for x in regs]

        # now we sort them by time/title
        classes.sort()

        for cls in classes:
            rooms = cls.prettyrooms()
            if len(rooms) == 0:
                rooms = u'N/A'
            else:
                rooms = u", ".join(rooms)

            schedule += u"""
%s|%s|%s""" % (u",".join(cls.friendly_times()).ljust(20),
               cls.title.ljust(25),
               rooms)

        return schedule


    class Meta:
        proxy = True
        app_label = 'modules'

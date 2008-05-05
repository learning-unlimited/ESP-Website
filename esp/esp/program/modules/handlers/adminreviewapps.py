
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
from esp.users.models import ESPUser, UserBit, User
from esp.web.util        import render_to_response
from esp.program.models import ClassSubject, JunctionStudentApp, JunctionAppReview
from django.contrib.auth.decorators import login_required
from esp.datatree.models import DataTree, GetNode
from django.http import HttpResponseRedirect
from esp.db.models import Q

__all__ = ['AdminReviewApps']

class AdminReviewApps(ProgramModuleObj, CoreModule):

    def students(self, QObject=False):
        accept_node = GetNode('V/Flags/Registration/Accepted')
        
        Q_accepted = Q(userbit__qsc__parent = self.program.classes_node()) &\
                     Q(userbit__verb = accept_node)

        if QObject:
            return {'app_accepted_to_one_program': Q_accepted}
        else:
            return {'app_accepted_to_one_program': User.objects.filter(Q_accepted).distinct()}

    def studentDesc(self):
        return {'app_accepted_to_one_program': """Students who are accepted to at least one class."""}
    
    @needs_admin
    def review_students(self, request, tl, one, two, module, extra, prog):
        """ Show a roster of the students in the class, allowing the administrators
        to accept students into the program based on the teachers' reviews and the
        students' applications. """
        
        accept_node = request.get_node('V/Flags/Registration/Accepted')
        try:
            cls = ClassSubject.objects.get(id = extra)
        except ClassSubject.DoesNotExist:
            raise ESPError(False), 'Cannot find class.'

        if not self.user.canEdit(cls):
            raise ESPError(False), 'You cannot edit class "%s"' % cls

        students = cls.students()

        for student in students:
            student.added_class = student.userbit_set.filter(qsc__rangestart__gte=cls.anchor.rangestart, qsc__rangeend__gte=cls.anchor.rangeend)[0].startdate
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
            if UserBit.objects.filter(user=student, qsc=cls.anchor, verb=accept_node).count() > 0:
                student.status = 'Accepted'
            else:
                student.status = 'Not accepted'

        students = list(students)
        students.sort(key=lambda x: x.last_name)

        return render_to_response(self.baseDir()+'roster.html',
                                  request,
                                  (prog, tl),
                                  {'class': cls,
                                   'students':students})

    @needs_admin
    def accept_student(self, request, tl, one, two, module, extra, prog):
        """ Accept a student into a class. """

        accept_node = request.get_node('V/Flags/Registration/Accepted')
        try:
            cls = ClassSubject.objects.get(id = request.GET.get('cls',''))
            student = User.objects.get(id = request.GET.get('student',''))
        except:
            raise ESPError(False), 'Student or class not found.'

        UserBit.objects.get_or_create(user=student, qsc=cls.anchor,
                                      verb=accept_node, recursive=False)
        return self.review_students(request, tl, one, two, module, extra, prog)
    
    @needs_admin
    def reject_student(self, request, tl, one, two, module, extra, prog):
        """ Reject a student from a class (does not affect their
        registration). """

        accept_node = request.get_node('V/Flags/Registration/Accepted')
        try:
            cls = ClassSubject.objects.get(id = request.GET.get('cls',''))
            student = User.objects.get(id = request.GET.get('student',''))
        except:
            raise ESPError(False), 'Student or class not found.'

        UserBit.objects.filter(user=student, qsc=cls.anchor, verb=accept_node, recursive=False).delete()
        
        return self.review_students(request, tl, one, two, module, extra, prog)
    
    @meets_deadline()
    @needs_teacher
    def review_student(self, request, tl, one, two, module, extra, prog):

        reg_node = request.get_node('V/Flags/Registration/Preliminary')

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

    @needs_admin
    def view_app(self, request, tl, one, two, module, extra, prog):
        reg_node = request.get_node('V/Flags/Registration/Preliminary')
        try:
            cls = ClassSubject.objects.get(id = extra)
        except ClassSubject.DoesNotExist:
            raise ESPError(False), 'Cannot find class.'
        
        student = request.GET.get('student',None)
        if not student:
            student = request.POST.get('student','')

        try:
            student = ESPUser(User.objects.get(id = student))
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
        
        return render_to_response(self.baseDir()+'app_popup.html', request, (prog, tl), {'class': cls, 'student': student})

    def prepare(self, context):
        """ Sets the 'classes' template variable to contain the list of classes that the current user is teaching """
        context['classes_to_review'] = self.program.classes()
        return context

    def isStep(self):
        return True

    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        if key == 'schedule_app':
            return AdminReviewApps.getSchedule(self.program, user)

        return None

    @staticmethod
    def getSchedule(program, student):
        accept_node = GetNode('V/Flags/Registration/Accepted')
        
        schedule = """
Student schedule for %s:

 Time               | Class                   | Room""" % student.name()


        classes = list(UserBit.find_by_anchor_perms(ClassSubject, student, accept_node).filter(parent_program = program))

        # now we sort them by time/title
        classes.sort()
        
        for cls in classes:
            rooms = cls.prettyrooms()
            if len(rooms) == 0:
                rooms = 'N/A'
            else:
                rooms = ", ".join(rooms)
                
            schedule += """
%s|%s|%s""" % (",".join(cls.friendly_times()).ljust(20),
               cls.title().ljust(25),
               rooms)
               
        return schedule


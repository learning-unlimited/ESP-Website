
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
from collections import defaultdict

from esp.program.modules.base    import ProgramModuleObj, needs_teacher, meets_deadline, main_call, aux_call, user_passes_test
from esp.program.modules.forms.teacherreg   import TeacherClassRegForm, TeacherOpenClassRegForm
from esp.program.models          import ClassSubject, ClassSection, Program, ProgramModule, StudentRegistration, RegistrationType, ClassFlagType, RegistrationProfile, ScheduleMap
from esp.program.controllers.classreg import ClassCreationController, ClassCreationValidationError, get_custom_fields
from esp.resources.models        import ResourceRequest
from esp.tagdict.models          import Tag
from esp.utils.web               import render_to_response
from esp.dbmail.models           import send_mail
from esp.middleware              import ESPError
from django.db.models.query      import Q
from esp.users.models            import User, ESPUser, Record, TeacherInfo
from esp.resources.forms         import ResourceRequestFormSet
from esp.mailman                 import add_list_members
from django.conf                 import settings
from django.http                 import HttpResponse, HttpResponseRedirect
from django.db                   import models
from django.forms.utils          import ErrorDict
from django.template.loader      import render_to_string
from esp.middleware.threadlocalrequest import get_current_request

import json
import re
import datetime
from copy import deepcopy

class TeacherClassRegModule(ProgramModuleObj):
    """ This program module allows teachers to register classes, and for them to modify classes/view class statuses
        as the program goes on. It is suggested, though not required, that this module is used in conjunction with
        StudentClassRegModule. Please be mindful of all the options of this module. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Class Registration",
            "link_title": "Register Your Classes",
            "module_type": "teach",
            "seq": 10,
            "inline_template": "listclasses.html",
            "choosable": 1,
            }

    @property
    def crmi(self):
        return self.program.classregmoduleinfo

    def prepare(self, context={}):
        """ prepare returns the context for the main teacherreg page. """

        context['can_edit'] = self.deadline_met('/Classes/Edit')
        context['can_create'] = self.any_reg_is_open()
        context['can_create_class'] = self.class_reg_is_open()
        context['can_create_open_class'] = self.open_class_reg_is_open()
        context['can_req_cancel'] = self.deadline_met('/Classes/CancelReq')
        context['survey_results'] = (self.program.getSurveys().filter(category = "learn", questions__per_class=True).exists() and
                                     self.program.getTimeSlots()[0].start < datetime.datetime.now())
        context['crmi'] = self.crmi
        context['clslist'] = self.clslist(get_current_request().user)
        context['friendly_times_with_date'] = Tag.getBooleanTag('friendly_times_with_date', self.program)
        context['open_class_category'] = self.program.open_class_category.category
        return context


    def noclasses(self):
        """ Returns true of there are no classes in this program """
        return not self.clslist(get_current_request().user).exists()

    def isCompleted(self):
        return not self.noclasses()

    def get_resource_pairs(self):
        items = []
        for res_type in self.program.getResourceTypes():
            possible_values = res_type.resourcerequest_set.values_list('desired_value', flat=True).distinct()
            for i in range(len(possible_values)):
                val = possible_values[i]
                label = 'teacher_res_%d_%d' % (res_type.id, i)
                full_description = 'Teachers who requested "%s" for their %s' % (val, res_type.name)
                query = Q(classsubject__sections__resourcerequest__res_type=res_type, classsubject__sections__resourcerequest__desired_value=val, classsubject__sections__parent_class__parent_program=self.program)
                items.append((label, full_description, query))
        return items

    def teachers(self, QObject = False):
        fields_to_defer = [x.name for x in ClassSubject._meta.fields if isinstance(x, models.TextField)]
        classes_qs = self.program.classes().defer(*fields_to_defer)

        Q_isteacher = Q(classsubject__in=classes_qs)
        Q_rejected_teacher = Q(classsubject__in=classes_qs.filter(status__lt=0)) & Q_isteacher
        Q_approved_teacher = Q(classsubject__in=classes_qs.filter(status__gt=0)) & Q_isteacher
        Q_proposed_teacher = Q(classsubject__in=classes_qs.filter(status=0)) & Q_isteacher

        ## is_nearly_full() means at least one section is more than float(ClassSubject.get_capacity_factor()) full
        ## isFull() means that all *scheduled* sections are full
        ## Querying the full catalog is overkill here, but we do use a fair bit of it..., and hopefully it's
        ## better cached than other simpler queries that we might use.
        classes = ClassSubject.objects.catalog(self.program)
        capacity_factor = ClassSubject.get_capacity_factor()
        nearly_full_classes = [x for x in classes if x.is_nearly_full(capacity_factor)]
        Q_nearly_full_teacher = Q(classsubject__in=nearly_full_classes) & Q_isteacher
        full_classes = [x for x in classes if x.isFull()]
        Q_full_teacher = Q(classsubject__in=full_classes) & Q_isteacher

        #   With the new schema it is impossible to make a single Q object for
        #   teachers who have taught for a previous program and teachers
        #   who are teaching for the current program.  You have to chain calls
        #   to .filter().
        Q_taught_before = Q(classsubject__status=10, classsubject__parent_program__in=Program.objects.exclude(pk=self.program.pk))

        #   Add dynamic queries for checking for teachers with particular resource requests
        additional_qs = {}
        for item in self.get_resource_pairs():
            additional_qs[item[0]] = Q_isteacher & (Q_rejected_teacher | Q_approved_teacher | Q_proposed_teacher) & item[2]

        if QObject:
            result = {
                'class_submitted': Q_isteacher,
                'class_approved': Q_approved_teacher,
                'class_proposed': Q_proposed_teacher,
                'class_rejected': Q_rejected_teacher,
                'class_nearly_full': Q_nearly_full_teacher,
                'class_full': Q_full_teacher,
                'taught_before': Q_taught_before,     #   not exactly correct, see above
            }
            for key in additional_qs:
                result[key] = additional_qs[key]
        else:
            result = {
                'class_submitted': ESPUser.objects.filter(Q_isteacher).distinct(),
                'class_approved': ESPUser.objects.filter(Q_approved_teacher).distinct(),
                'class_proposed': ESPUser.objects.filter(Q_proposed_teacher).distinct(),
                'class_rejected': ESPUser.objects.filter(Q_rejected_teacher).distinct(),
                'class_nearly_full': ESPUser.objects.filter(Q_nearly_full_teacher).distinct(),
                'class_full': ESPUser.objects.filter(Q_full_teacher).distinct(),
                'taught_before': ESPUser.objects.filter(Q_isteacher).filter(Q_taught_before).distinct(),
            }
            for key in additional_qs:
                result[key] = ESPUser.objects.filter(additional_qs[key]).distinct()

        return result

    def teacherDesc(self):
        capacity_factor = ClassSubject.get_capacity_factor()
        result = {
            'class_submitted': """Teachers who have submitted at least one class""",
            'class_approved': """Teachers teaching an approved class""",
            'class_proposed': """Teachers teaching an unreviewed class""",
            'class_rejected': """Teachers teaching a rejected class""",
            'class_full': """Teachers teaching a completely full class""",
            'class_nearly_full': """Teachers teaching a nearly-full class (>%d%% of capacity)""" % (100 * capacity_factor),
            'taught_before': """Teachers who have taught for a previous program""",
        }
        for item in self.get_resource_pairs():
            result[item[0]] = item[1]
        return result

    def deadline_met(self, extension=''):
        tmpModule = super(TeacherClassRegModule, self)
        if len(extension) > 0:
            return tmpModule.deadline_met(extension)
        else:
            return (self.any_reg_is_open()
                    or tmpModule.deadline_met('/Classes/Edit'))

    def class_reg_is_open(self):
        return self.deadline_met('/Classes/Create/Class')

    def open_class_reg_is_open(self):
        return (self.crmi.open_class_registration
                and self.deadline_met('/Classes/Create/OpenClass'))

    reg_is_open_methods = defaultdict(
        (lambda: (lambda self: False)),
        {
            'Class': class_reg_is_open,
            'OpenClass': open_class_reg_is_open,
        },
    )

    def reg_is_open(self, reg_type='Class'):
        return self.reg_is_open_methods[reg_type](self)

    def any_reg_is_open(self):
        return any(map(self.reg_is_open, self.reg_is_open_methods.keys()))

    def clslist(self, user):
        return user.getTaughtClasses(program = self.program, include_rejected = True)

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def section_attendance(self, request, tl, one, two, module, extra, prog):
        context = {'program': prog, 'tl': tl, 'one': one, 'two': two}

        user = request.user
        context['sched_sections'] = [sec for sec in user.getTaughtSections(program = prog) if sec.meeting_times.count() > 0]

        secid = 0
        if 'secid' in request.POST:
            secid = request.POST['secid']
        elif 'secid' in request.GET:
            secid = request.GET['secid']
        else:
            secid = extra
        sections = ClassSection.objects.filter(id = secid)
        if len(sections) == 1:
            if not request.user.canEdit(sections[0].parent_class):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
            else:
                section = sections[0]
                context['section'], context['not_found'] = self.process_attendance(section, request, prog)

        return render_to_response(self.baseDir()+'section_attendance.html', request, context)

    @staticmethod
    def process_attendance(section, request, prog):
        today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        attended = RegistrationType.objects.get_or_create(name = 'Attended', category = "student")[0]
        enrolled = RegistrationType.objects.get_or_create(name='Enrolled', category = "student")[0]
        onsite = RegistrationType.objects.get_or_create(name='OnSite/AttendedClass', category = "student")[0]
        not_found = []
        if request.POST and 'submitted' in request.POST:
            # split with delimiters comma, semicolon, and space followed by any amount of extra whitespace
            misc_students = filter(None, re.split(r'[;,\s]\s*', request.POST.get('misc_students')))
            for code in misc_students:
                try:
                    student = ESPUser.objects.get(id=code)
                except (ValueError, ESPUser.DoesNotExist):
                    try:
                        student = ESPUser.objects.get(username=code)
                    except (ValueError, ESPUser.DoesNotExist):
                        not_found.append(code)
                        continue
                if student.isStudent():
                    if not prog.isCheckedIn(student):
                        rec = Record(user=student, program=prog, event='attended')
                        rec.save()
                    sr = StudentRegistration.objects.get_or_create(user = student, section = section, relationship = attended, start_date__range=(today_min, today_max))[0]
                    sr.end_date = today_max
                    sr.save()
                    if student not in section.students():
                        if 'unenroll' in request.POST:
                            sm = ScheduleMap(student, prog)
                            for ts in [ts.id for ts in section.get_meeting_times()]:
                                if ts in sm.map and len(sm.map[ts]) > 0:
                                    for sm_sec in sm.map[ts]:
                                        sm_sec.unpreregister_student(student)
                        if 'enroll' in request.POST:
                            for rt in [enrolled, onsite]:
                                srs = StudentRegistration.objects.filter(user = student, section = section, relationship = rt)
                                if srs.count() > 0:
                                    sr = srs[0]
                                    sr.unexpire()
                                else:
                                    sr = StudentRegistration.objects.create(user = student, section = section, relationship = rt)
                                if rt.name=='OnSite/AttendedClass':
                                    sr.end_date = today_max
                                    sr.save()

        section.enrolled_list = []
        section.attended_list = []
        for student in section.students():
            student.checked_in = prog.isCheckedIn(student)
            student.attended = StudentRegistration.valid_objects().filter(user = student, section = section, relationship = attended).exists()
            section.enrolled_list.append(student)
        section.enrolled_list.sort(key=lambda student: student.last_name)
        for student in section.students(["Attended"]):
            if student not in section.students():
                student.checked_in = prog.isCheckedIn(student)
                student.attended = StudentRegistration.valid_objects().filter(user = student, section = section, relationship = attended).exists()
                section.attended_list.append(student)
        return (section, not_found)

    @aux_call
    @needs_teacher
    def ajaxstudentattendance(self, request, tl, one, two, module, extra, prog):
        """
        POST to this view to change the attendance status of a student for a given section.
        POST data:
          'student':              The teacher's username.
          'secid':                The section ID.
          'undo' (optional):      If 'true', expires all attendance registrations
                                  for the student for the section.
                                  Otherwise, the student is marked as attending the section.
          'enroll' (optional):    If 'false', does not enroll the student in the section.
                                  Otherwise, enrolls the student if they are not already enrolled.
          'unenroll' (optional):  If 'false', does not unenroll the student from conflicting sections.
                                  Otherwise, unenrolls the student from conflicting sections.
        """
        json_data = {}
        today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        attended = RegistrationType.objects.get_or_create(name = 'Attended', category = "student")[0]
        enrolled = RegistrationType.objects.get_or_create(name='Enrolled', category = "student")[0]
        onsite = RegistrationType.objects.get_or_create(name='OnSite/AttendedClass', category = "student")[0]
        if 'student' in request.POST and 'secid' in request.POST:
            students = ESPUser.objects.filter(username=request.POST['student'])
            if not students.exists():
                json_data['error'] = 'User with username %s not found!' % request.POST['student']
            else:
                student = students[0]
                json_data['name'] = student.name()
                sections = ClassSection.objects.filter(id=request.POST['secid'])
                if not sections.exists():
                    json_data['error'] = 'Section with ID %s not found!' % request.POST['secid']
                else:
                    section = sections[0]
                    json_data['secid'] = section.id
                    if request.POST.get('undo', 'false').lower() == 'true':
                        #should we also delete the program attendance record?
                        srs = StudentRegistration.valid_objects().filter(user = student, section = section, relationship = attended)
                        if srs.exists():
                            for sr in srs:
                                sr.expire() #or delete??
                            json_data['message'] = '%s is no longer marked as attending.' % student.name()
                        else:
                            json_data['message'] = '%s was not marked as attending.' % student.name()
                    else:
                        if not prog.isCheckedIn(student):
                            rec = Record(user=student, program=prog, event='attended')
                            rec.save()
                            json_data['checkedin'] = True
                        sr = StudentRegistration.objects.get_or_create(user = student, section = section, relationship = attended, start_date__range=(today_min, today_max))[0]
                        sr.end_date = today_max
                        sr.save()
                        if student not in section.students():
                            if request.POST.get('unenroll', 'true').lower() == 'true':
                                sm = ScheduleMap(student, prog)
                                for ts in [ts.id for ts in section.get_meeting_times()]:
                                    if ts in sm.map and len(sm.map[ts]) > 0:
                                        for sm_sec in sm.map[ts]:
                                            sm_sec.unpreregister_student(student)
                            if request.POST.get('enroll', 'true').lower() == 'true':
                                for rt in [enrolled, onsite]:
                                    srs = StudentRegistration.objects.filter(user = student, section = section, relationship = rt)
                                    if srs.count() > 0:
                                        sr = srs[0]
                                        sr.unexpire()
                                    else:
                                        sr = StudentRegistration.objects.create(user = student, section = section, relationship = rt)
                                    if rt.name=='OnSite/AttendedClass':
                                        sr.end_date = today_max
                                        sr.save()
                        json_data['message'] = '%s is marked as attending.' % student.name()
        return HttpResponse(json.dumps(json_data), content_type='text/json')

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def section_students(self, request, tl, one, two, module, extra, prog):
        secid = 0
        if 'secid' in request.POST:
            secid = request.POST['secid']
        else:
            secid = extra
        sections = ClassSection.objects.filter(id = secid)
        if len(sections) != 1 or not request.user.canEdit(sections[0].parent_class):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        section = sections[0]

        return render_to_response(self.baseDir()+'class_students.html', request, {'section': section, 'cls': section})

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def class_students(self, request, tl, one, two, module, extra, prog):
        clsid = 0
        if 'clsid' in request.POST:
            clsid = request.POST['clsid']
        else:
            clsid = extra
        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        return render_to_response(self.baseDir()+'class_students.html', request, {'cls': cls})

    @aux_call
    @needs_teacher
    @meets_deadline('/Classes')
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]
        if cls.num_students() > 0:
            return render_to_response(self.baseDir()+'toomanystudents.html', request, {})

        cls.delete()
        return self.goToCore(tl)

    @aux_call
    @needs_teacher
    def cancelrequest(self, request, tl, one, two, module, extra, prog):
        if request.method == "POST" and 'reason' in request.POST:
            cls = ClassSubject.objects.get(id=request.POST['cls'])
            reason = request.POST['reason']
            request_teacher = request.user

            email_title = '[%s] Class Cancellation Request for %s: %s' % (self.program.niceName(), cls.emailcode(), cls.title)
            email_from = '%s Registration System <server@%s>' % (self.program.program_type, settings.EMAIL_HOST_SENDER)
            email_context = {'request_teacher': request_teacher,
                             'program': self.program,
                             'cls': cls,
                             'reason': reason,
                             'DEFAULT_HOST': settings.DEFAULT_HOST,
                             'one': cls.parent_program.program_type,
                             'two': cls.parent_program.program_instance}

            #Send email to all teachers confirming cancellation request
            email_contents = render_to_string('program/modules/teacherclassregmodule/cancelrequest.txt', email_context)
            for teacher in cls.get_teachers():
                email_to = ['%s <%s>' % (teacher.name(), teacher.email)]
                send_mail(email_title, email_contents, email_from, email_to, False)

            #Send email to admin with link to manageclass page
            email_context['admin'] = True
            email_contents = render_to_string('program/modules/teacherclassregmodule/cancelrequest.txt', email_context)
            email_to = ['Directors <%s>' % (cls.parent_program.director_email)]
            send_mail(email_title, email_contents, email_from, email_to, False)

        return self.goToCore(tl)

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def class_status(self, request, tl, one, two, module, extra, prog):
        clsid = 0
        if 'clsid' in request.POST:
            clsid = request.POST['clsid']
        else:
            clsid = extra

        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        context = {'cls': cls, 'module': self,}

        return render_to_response(self.baseDir()+'class_status.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline("/MainPage")
    def class_docs(self, request, tl, one, two, module, extra, prog):
        from esp.web.forms.fileupload_form import FileUploadForm
        from esp.qsdmedia.models import Media

        clsid = 0
        if 'clsid' in request.POST:
            clsid = request.POST['clsid']
        else:
            clsid = extra

        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})

        target_class = classes[0]
        context_form = FileUploadForm()

        if request.method == 'POST':
            if request.POST['command'] == 'delete':
                docid = request.POST['docid']
                media = Media.objects.get(id = docid)
                media.delete()
            elif request.POST['command'] == 'add':
                form = FileUploadForm(request.POST, request.FILES)

                if form.is_valid():
                    media = Media(friendly_name = form.cleaned_data['title'], owner = target_class)
                    ufile = form.cleaned_data['uploadedfile']

                    #	Append the class code on the filename
                    desired_filename = '%s_%s' % (target_class.emailcode(), ufile.name)
                    media.handle_file(ufile, desired_filename)

                    media.format = ''
                    media.save()
                else:
                    context_form = form

        context = {'cls': target_class, 'uploadform': context_form, 'module': self}

        return render_to_response(self.baseDir()+'class_docs.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline('/Classes/Coteachers')
    def coteachers(self, request, tl, one, two, module, extra, prog):
        if not 'clsid' in request.POST:
            return self.goToCore(tl) # just fails.

        if extra == 'nojs':
            ajax = False
        else:
            ajax = True

        classes = ClassSubject.objects.filter(id = request.POST['clsid'])
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})

        cls = classes[0]

        # set txtTeachers and coteachers....
        if not 'coteachers' in request.POST:
            coteachers = cls.get_teachers()
            coteachers = [ user for user in coteachers
                           if user.id != request.user.id           ]

            txtTeachers = ",".join([str(user.id) for user in coteachers ])

        else:
            txtTeachers = request.POST['coteachers']
            coteachers = txtTeachers.split(',')
            coteachers = [ x for x in coteachers if x != '' ]
            coteachers = [ ESPUser.objects.get(id=userid)
                           for userid in coteachers                ]
            add_list_members("%s_%s-teachers" % (prog.program_type, prog.program_instance), coteachers)

        op = ''
        if 'op' in request.POST:
            op = request.POST['op']

        error = False

        old_coteachers_set = set(cls.get_teachers())
        ccc = ClassCreationController(self.program)

        conflictinguser = ''

        if op == 'add':

            if len(request.POST['teacher_selected'].strip()) == 0:
                error = 'Error - Please click on the name when it drops down.'

            elif (request.POST['teacher_selected'] == str(request.user.id)):
                error = 'Error - You cannot select yourself as a coteacher!'
            elif request.POST['teacher_selected'] in txtTeachers.split(','):
                error = 'Error - You already added this teacher as a coteacher!'

            if error:
                return render_to_response(self.baseDir()+'coteachers.html', request, {'class':cls,
                                                                                     'ajax':ajax,
                                                                                     'txtTeachers': txtTeachers,
                                                                                     'coteachers':  coteachers,
                                                                                     'error': error,
                                                                                     'conflict': []})

            # add schedule conflict checking here...
            teacher = ESPUser.objects.get(id = request.POST['teacher_selected'])

            if cls.conflicts(teacher):
                conflictinguser = (teacher.first_name+' '+teacher.last_name)
            else:
                lastProf = RegistrationProfile.getLastForProgram(teacher, prog)
                if not lastProf.teacher_info:
                    anyInfo = teacher.getLastProfile().teacher_info
                    if anyInfo:
                        lastProf.teacher_info = TeacherInfo.addOrUpdate(teacher, lastProf,
                                                                        {'graduation_year': anyInfo.graduation_year,
                                                                         'affiliation': anyInfo.affiliation,
                                                                         'major': anyInfo.major,
                                                                         'shirt_size': anyInfo.shirt_size,
                                                                         'shirt_type': anyInfo.shirt_type})
                    else:
                        lastProf.teacher_info = TeacherInfo.addOrUpdate(teacher, lastProf, {})
                lastProf.save()
                coteachers.append(teacher)
                txtTeachers = ",".join([str(coteacher.id) for coteacher in coteachers ])
                ccc.associate_teacher_with_class(cls, teacher)
                ccc.send_class_mail_to_directors(cls)

        elif op == 'del':
            ids = request.POST.getlist('delete_coteachers')
            newcoteachers = []
            for coteacher in coteachers:
                if str(coteacher.id) not in ids:
                    newcoteachers.append(coteacher)

            coteachers = newcoteachers
            txtTeachers = ",".join([str(coteacher.id) for coteacher in coteachers ])

            new_coteachers_set = set(coteachers)
            to_be_deleted = old_coteachers_set - new_coteachers_set

            if request.user in to_be_deleted:
                to_be_deleted.remove(request.user)

            for teacher in to_be_deleted:
                cls.removeTeacher(teacher)

            ccc.send_class_mail_to_directors(cls)

        return render_to_response(self.baseDir()+'coteachers.html', request, {'class':cls,
                                                                             'ajax':ajax,
                                                                             'txtTeachers': txtTeachers,
                                                                             'coteachers':  coteachers,
                                                                             'conflict':    conflictinguser})

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/Edit")
    def editclass(self, request, tl, one, two, module, extra, prog):
        try:
            int(extra)
        except:
            raise ESPError("Invalid integer for class ID!", log=False)

        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) == 0:
            raise ESPError("No class found matching this ID!", log=False)

        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        if cls.category == self.program.open_class_category:
            action = 'editopenclass'
        else:
            action = 'edit'

        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, cls, action)

    @main_call
    @needs_teacher
    @meets_deadline('/Classes/Create/Class')
    def makeaclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, newclass = None)

    @aux_call
    @needs_teacher
    @meets_deadline('/Classes/Create/Class')
    def copyaclass(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            action = 'create'
            if 'category' in request.POST:
                category = request.POST['category']
                if category.isdigit() and int(category) == int(self.program.open_class_category.id):
                    action = 'createopenclass'
            return self.makeaclass_logic(request, tl, one, two, module, extra, prog, action=action)
        if not 'cls' in request.GET:
            raise ESPError("No class specified!", log=False)

        # Select the class
        cls_id = request.GET['cls']
        classes = ClassSubject.objects.filter(id=cls_id)
        if len(classes) == 0:
            raise ESPError("No class found matching this ID!", log=False)
        if len(classes) != 1:
            raise ESPError("Something weird happened, more than one class found matching this ID.", log=False)
        cls = classes[0]

        # Select the correct action
        if cls.category == self.program.open_class_category:
            action = 'editopenclass'
        else:
            action = 'edit'

        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, cls, action, populateonly = True)

    @aux_call
    @needs_teacher
    @meets_deadline('/Classes/Create/Class')
    def copyclasses(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['all_class_list'] = request.user.getTaughtClasses()
        context['noclasses'] = (len(context['all_class_list']) == 0)
        return render_to_response(self.baseDir()+'listcopyclasses.html', request, context)

    @aux_call
    @needs_teacher
    @user_passes_test(
        open_class_reg_is_open,
        (
            'the deadline Teacher/Classes/Create/OpenClass '
            'or the setting ClassRegModuleInfo.open_class_registration were'
        ),
    )
    def makeopenclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, newclass = None, action = 'createopenclass')


    def makeaclass_logic(self, request, tl, one, two, module, extra, prog, newclass = None, action = 'create', populateonly = False):
        """
        The logic for the teacher class registration form.

        A brief description of some of the key arguments:
        - newclass -- The class object from which to fill in the data
        - action -- What action is the form performing? Options are 'create',
              'createopenclass', 'edit', 'editopenclass'
        - populateonly -- If True and newclass is specified, the form will only
              populate the fields, rather than keeping track of which class they
              came from and saving edits back to that. This is used for the class
              copying logic.
        """

        context = {'module': self}

        if request.method == 'POST' and 'class_reg_page' in request.POST:
            if not self.deadline_met():
                return self.goToCore(tl)

            ccc = ClassCreationController(self.program)

            try:
                if action == 'create':
                    newclass = ccc.makeaclass(request.user, request.POST)
                elif action == 'createopenclass':
                    newclass = ccc.makeaclass(request.user, request.POST, form_class=TeacherOpenClassRegForm)
                elif action == 'edit':
                    newclass = ccc.editclass(request.user, request.POST, extra)
                elif action == 'editopenclass':
                    newclass = ccc.editclass(request.user, request.POST, extra, form_class=TeacherOpenClassRegForm)

                do_question = bool(ProgramModule.objects.filter(handler="TeacherReviewApps", program=self.program))

                if do_question:
                    return HttpResponseRedirect(newclass.parent_program.get_teach_url() + "app_questions")
                if request.POST.get('manage') == 'manage':
                    if request.POST['manage_submit'] == 'reload':
                        return HttpResponseRedirect(request.get_full_path()+'?manage=manage')
                    elif request.POST['manage_submit'] == 'manageclass':
                        return HttpResponseRedirect('/manage/%s/manageclass/%s' % (self.program.getUrlBase(), extra))
                    elif request.POST['manage_submit'] == 'dashboard':
                        return HttpResponseRedirect('/manage/%s/dashboard' % self.program.getUrlBase())
                    elif request.POST['manage_submit'] == 'main':
                        return HttpResponseRedirect('/manage/%s/main' % self.program.getUrlBase())
                return self.goToCore(tl)

            except ClassCreationValidationError, e:
                reg_form = e.reg_form
                resource_formset = e.resource_formset

        else:
            # With static resource requests, we need to display a form
            # each available type --- there's no way to add the types
            # that we didn't start out with
            # Thus, if default_restype isn't set, we display everything
            # potentially relevant
            resource_types = prog.getResourceTypes(include_classroom=True,
                                                   include_global=Tag.getBooleanTag('allow_global_restypes'),
                                                   include_hidden=False)
            resource_types = list(resource_types)
            resource_types.reverse()

            if newclass is not None:
                current_data = newclass.__dict__
                # Duration can end up with rounding errors. Pick the closest.
                old_delta = None
                # Technically, this is a "backwards compatibility" field, so we put in a hack
                # for the "correct" usage. This feels silly. Why are ClassSections allowed different
                # durations when every interface assumes they're identical?
                current_duration = current_data['duration'] or newclass.sections.all()[0].duration
                rounded_duration = 0
                for k, v in self.crmi.getDurations() + [(0,'')]:
                    new_delta = abs( k - current_duration )
                    if old_delta is None or new_delta < old_delta:
                        old_delta = new_delta
                        rounded_duration = k
                current_data['duration'] = rounded_duration
                current_data['category'] = newclass.category.id
                current_data['num_sections'] = newclass.sections.count()
                current_data['allow_lateness'] = newclass.allow_lateness
                current_data['title'] = newclass.title
                current_data['url']   = newclass.emailcode()
                min_grade = newclass.grade_min
                max_grade = newclass.grade_max
                if Tag.getProgramTag('grade_ranges', prog):
                    current_data['grade_range'] = [min_grade,max_grade]
                for field_name in get_custom_fields():
                    if field_name in newclass.custom_form_data:
                        current_data[field_name] = newclass.custom_form_data[field_name]
                if newclass.optimal_class_size_range:
                    current_data['optimal_class_size_range'] = newclass.optimal_class_size_range.id
                if newclass.allowable_class_size_ranges.all():
                    current_data['allowable_class_size_ranges'] = list(newclass.allowable_class_size_ranges.all().values_list('id', flat=True))

                # Makes importing a class from a previous program work
                # These are the only three fields that can currently be hidden
                # If another one is added later, this will need to be changed
                hidden_fields = Tag.getProgramTag('teacherreg_hide_fields', prog)
                if hidden_fields:
                    if 'grade_min' in hidden_fields:
                        current_data['grade_min'] = Tag.getProgramTag('teacherreg_default_min_grade', prog)
                    if 'grade_max' in hidden_fields:
                        current_data['grade_max'] = Tag.getProgramTag('teacherreg_default_max_grade', prog)
                    if 'class_size_max' in hidden_fields:
                        current_data['class_size_max'] = Tag.getProgramTag('teacherreg_default_class_size_max', prog)

                if not populateonly:
                    context['class'] = newclass

                if action=='edit':
                    reg_form = TeacherClassRegForm(self.crmi, current_data)
                    # TODO: remove private API use
                    if populateonly: reg_form._errors = ErrorDict()
                elif action=='editopenclass':
                    reg_form = TeacherOpenClassRegForm(self.crmi, current_data)
                    # TODO: remove private API use
                    if populateonly: reg_form._errors = ErrorDict()

                #   Todo...
                ds = newclass.default_section()
                class_requests = ResourceRequest.objects.filter(target=ds)
                #   Program the multiple-checkbox forms if static requests are used.
                resource_formset = ResourceRequestFormSet(resource_type=resource_types, prefix='request')
                initial_requests = {}
                for x in class_requests:
                    if x.res_type.name not in initial_requests:
                        initial_requests[x.res_type.name]  = []
                    initial_requests[x.res_type.name].append(x.desired_value)
                for form in resource_formset.forms:
                    field = form.fields['desired_value']
                    if field.label in initial_requests:
                        field.initial = initial_requests[field.label]
                        if form.resource_type.only_one and len(field.initial):
                            field.initial = field.initial[0]

            else:
                if action=='create':
                    reg_form = TeacherClassRegForm(self.crmi)
                elif action=='createopenclass':
                    reg_form = TeacherOpenClassRegForm(self.crmi)

                #   Provide initial forms: a request for each provided type, but no requests for new types.
                resource_formset = ResourceRequestFormSet(resource_type=resource_types, prefix='request')

        context['tl'] = 'teach'
        context['one'] = one
        context['two'] = two
        context['form'] = reg_form
        context['formset'] = resource_formset
        context['resource_types'] = self.program.getResourceTypes(include_classroom=True)
        context['classroom_form_advisories'] = 'classroom_form_advisories'
        context['grade_range_popup'] = Tag.getBooleanTag('grade_range_popup', self.program)

        if newclass is None:
            context['addoredit'] = 'Add'
        else:
            context['addoredit'] = 'Edit'

        context['classes'] = {
            0: {
                'type': 'class',
                'link': 'makeaclass',
                'reg_open': self.class_reg_is_open(),
            },
            1: {
                'type': self.program.open_class_category.category,
                'link': 'makeopenclass',
                'reg_open': self.open_class_reg_is_open(),
            }
        }
        if action == 'create' or action == 'edit':
            context['isopenclass'] = 0
        elif action == 'createopenclass' or action == 'editopenclass':
            context['isopenclass'] = 1
            context['grade_range_popup'] = False
            context['classroom_form_advisories'] += '__open_class'
        context['classtype'] = context['classes'][context['isopenclass']]['type']
        context['otherclass'] = context['classes'][1 - context['isopenclass']]
        context['qsd_name'] = 'classedit_' + context['classtype']

        context['manage'] = False
        if ((request.method == "POST" and request.POST.get('manage') == 'manage') or
            (request.method == "GET" and request.GET.get('manage') == 'manage') or
            (tl == 'manage' and 'class' in context)) and request.user.isAdministrator():
            context['manage'] = True
            if self.program.program_modules.filter(handler='ClassFlagModule').exists():
                context['show_flags'] = True
                context['flag_types'] = ClassFlagType.get_flag_types(self.program)

        return render_to_response(self.baseDir() + 'classedit.html', request, context)


    @aux_call
    @needs_teacher
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):

        # Search for teachers with names that start with search string
        if not 'name' in request.GET or 'name' in request.POST:
            return self.goToCore(tl)

        return TeacherClassRegModule.teacherlookup_logic(request, tl, one, two, module, extra, prog, newclass)

    @staticmethod
    def teacherlookup_logic(request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json_utils import JsonResponse

        Q_teacher = Q(groups__name="Teacher")

        queryset = ESPUser.objects.filter(Q_teacher)

        if not 'name' in request.GET:
            startswith = request.POST['name']
        else:
            startswith = request.GET['name']
        s = ''
        spaces = ''
        after_comma = False
        for char in startswith:
            if char == ' ':
                if not after_comma:
                    spaces += ' '
            elif char == ',':
                s += ','
                spaces = ''
                after_comma = True
            else:
                s += spaces + char
                spaces = ''
                after_comma = False
        startswith = s
        parts = [x.strip('*') for x in startswith.split(',')]

        #   Don't return anything if there's no input.
        if len(parts[0]) > 0:
            Q_name = Q(last_name__istartswith=parts[0])

            if len(parts) > 1:
                Q_name = Q_name & Q(first_name__istartswith=parts[1])

            # Isolate user objects
            queryset = queryset.filter(Q_name)[:(limit*10)]
            user_dict = {}
            for user in queryset:
                user_dict[user.id] = user
            users = user_dict.values()

            # Construct combo-box items
            obj_list = [{'name': "%s, %s" % (user.last_name, user.first_name), 'username': user.username, 'id': user.id} for user in users]
        else:
            obj_list = []

        return JsonResponse(obj_list)

    def get_msg_vars(self, user, key):
        if key == 'full_classes':
            return user.getFullClasses_pretty(self.program)

        return 'No classes.'

    class Meta:
        proxy = True
        app_label = 'modules'

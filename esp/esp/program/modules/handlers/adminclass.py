
from __future__ import absolute_import
from __future__ import division
from six.moves import range
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
from esp.program.class_status import ClassStatus
from esp.program.modules.base import ProgramModuleObj, needs_admin, aux_call
from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule

from esp.cal.models import Event
from esp.program.models import ClassSubject, ClassSection, ClassFlagType
from esp.tagdict.models import Tag

from esp.utils.web import render_to_response
from esp.program.modules.forms.management import ClassManageForm, SectionManageForm, ClassCancellationForm, SectionCancellationForm

from django.http import HttpResponseRedirect, HttpResponse
from esp.middleware import ESPError
from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC

""" Module in the middle of a rewrite. -Michael """

class AdminClass(ProgramModuleObj):
    doc = """This module is extremely useful for managing classes if you have them in your program.
        Works best with student and teacher class modules, but they are not necessary.
        Options for this are available on the main manage page.
        """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Class Management for Admin",
            "link_title": "Manage Classes",
            "module_type": "manage",
            "inline_template": "listclasses.html",
            "seq": 1,
            "choosable": 1,
            }

    form_choice_types = ['status', 'reg_status', 'room', 'resources', 'times', 'min_grade', 'max_grade', 'duration']
    def getFormChoices(self, field_str):
        """ A more compact function for zipping up the options available on class
        management forms. """

        if field_str == 'status':
            return ((ClassStatus.CANCELLED, 'Cancelled'), (ClassStatus.REJECTED, 'Rejected'), (ClassStatus.UNREVIEWED, 'Unreviewed'), (ClassStatus.HIDDEN, 'Accepted but hidden'), (ClassStatus.ACCEPTED, 'Accepted'))
        if field_str == 'reg_status':
            return (('', 'Leave unchanged'), (0, 'Open'), (10, 'Closed'))
        if field_str == 'room':
            room_choices = list(self.program.getClassrooms().values_list('name', 'name').order_by('name').distinct())
            return [(None, 'Unassigned')] + room_choices
        if field_str == 'resources':
            resources = self.program.getFloatingResources()
            return ((x.name, x.name) for x in resources)
        if field_str == 'times':
            return self.program.getTimeSlots().values_list('id', 'short_description')
        if field_str == 'min_grade' or field_str == 'max_grade':
            min_grade, max_grade = (7, 12)
            if self.program.grade_min:
                min_grade = self.program.grade_min
            if self.program.grade_max:
                max_grade = self.program.grade_max
            return ((i, str(i)) for i in range(min_grade, max_grade + 1))
        if field_str == 'duration':
            return self.program.getDurations()

    def timeslot_counts(self):
        timeslots = self.program.getTimeSlots()
        clsTimeSlots = []
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.short_time()}
            section_list = self.program.sections().filter(meeting_times=timeslot)
            curTimeslot['classcount'] = section_list.count()
            clsTimeSlots.append(curTimeslot)
        return clsTimeSlots

    def getClasses(self):
        return ClassSubject.objects.catalog(self.program, force_all=True, order_args_override=['id'])

    def prepare(self, context=None):
        if context is None: context = {}
        classes = self.getClasses()
        context['noclasses'] = (len(classes) == 0)
        context['classes']   = classes
        return context

    def getClassFromId(self, request, clsid):
        try:
            clsid = int(clsid)
        except ValueError:
            message = 'Invalid class ID %s.' % clsid
            raise ESPError(message, log=False)

        try:
            cls = ClassSubject.objects.get(id = clsid, parent_program = self.program)
        except ClassSubject.DoesNotExist:
            message = 'Unable to find class %s.' % clsid
            raise ESPError(message, log=False)

        return cls

    def getClass(self, request, extra):
        clsid = None
        if extra is not None and len(extra.strip()) > 0:
            clsid = extra
        elif 'clsid' in request.POST:
            clsid = request.POST['clsid']
        elif 'clsid' in request.GET:
            clsid = request.GET['clsid']

        return self.getClassFromId(request, clsid)

    @aux_call
    @needs_admin
    def reviewClass(self, request, tl, one, two, module, extra, prog):
        """ Set the review status of a class """
        if request.method == 'POST':
            if not ('class_id' in request.POST and 'review_status' in request.POST):
                raise ESPError("Error: missing data on request")

            class_id = request.POST['class_id']
            try:
                class_subject = ClassSubject.objects.get(pk=class_id)
            except ClassSubject.MultipleObjectsReturned:
                raise ESPError("Error: multiple classes selected")
            except ClassSubject.DoesNotExist:
                raise ESPError("Error: no classes found with id "+str(class_id))

            review_status = request.POST['review_status']

            if review_status == 'ACCEPT':
                class_subject.accept()
            elif review_status == 'UNREVIEW':
                class_subject.propose()
            elif review_status == 'REJECT':
                class_subject.reject()
            elif review_status == 'CANCEL':
                class_subject.cancel()
            else:
                raise ESPError("Error: invalid review status")

        return HttpResponse('')

    @aux_call
    @needs_admin
    def deletesection(self, request, tl, one, two, module, extra, prog):
        """ A little function to remove the section specified in POST. """
        if request.method == 'POST':
            if request.POST.get('sure') == 'True':
                try:
                    s = ClassSection.objects.get(id=int(request.GET['sec_id']))
                    s.delete()
                    return HttpResponseRedirect('/manage/%s/%s/manageclass/%s' % (one, two, extra))
                except:
                    raise ESPError('Unable to delete a section.  The section requested was: %s' % request.GET['sec_id'], log=False)
        else:
            section_id = int(request.GET['sec_id'])
            section = ClassSection.objects.get(id=section_id)
            context = {'sec': section, 'module': self}

            return render_to_response(self.baseDir()+'delete_confirm.html', request, context)

    @aux_call
    @needs_admin
    def addsection(self, request, tl, one, two, module, extra, prog):
        """ A little function to add a section to the class specified in POST. """
        cls = self.getClass(request, extra)
        cls.add_section()

        return HttpResponseRedirect('/manage/%s/%s/manageclass/%s' % (one, two, extra))

    @aux_call
    @needs_admin
    def manageclass(self, request, tl, one, two, module, extra, prog):
        cls = self.getClass(request, extra)
        sections = cls.sections.all().order_by('id')
        context = {}

        if cls.isCancelled() or not cls.hasScheduledSections():
            cls_cancel_form = None
        else:
            cls_cancel_form = ClassCancellationForm(subject=cls)
        sec_cancel_forms = SectionCancellationForm(cls = cls)

        cls_form = ClassManageForm(self, subject=cls)
        sec_forms = [SectionManageForm(self, section=sec, prefix='sec'+str(sec.index())) for sec in cls.sections.all().order_by('id')]

        action = request.GET.get('action', None)
        if request.method == 'POST':
            if action == 'cancel_cls':
                cls_cancel_form.data = request.POST
                cls_cancel_form.is_bound = True
                if cls_cancel_form.is_valid():
                    #   Call the Class{Subject,Section}.cancel() method to email and remove students, etc.
                    cls_cancel_form.cleaned_data['target'].cancel(email_students=True, include_lottery_students=cls_cancel_form.cleaned_data['email_lottery_students'], text_students=cls_cancel_form.cleaned_data['text_students'], email_teachers = cls_cancel_form.cleaned_data['email_teachers'], explanation=cls_cancel_form.cleaned_data['explanation'], unschedule=cls_cancel_form.cleaned_data['unschedule'])
                    return HttpResponseRedirect(request.get_full_path()) # Other forms may need updating, so just reload this view
            elif action == 'cancel_sec':
                sec_cancel_forms.data = request.POST
                sec_cancel_forms.is_bound = True
                if sec_cancel_forms.is_valid():
                    cleaned_data = sec_cancel_forms.cleaned_data
                    for sec in sections:
                        if not sec.isCancelled() and sec in cleaned_data['target']:
                            sec.cancel(email_students=True, include_lottery_students=cleaned_data['email_lottery_students'], text_students=cleaned_data['text_students'], email_teachers = cleaned_data['email_teachers'], explanation=cleaned_data['explanation'], unschedule=cleaned_data['unschedule'])
                    return HttpResponseRedirect(request.get_full_path()) # Other forms may need updating, so just reload this view
            elif action == 'modify_cls':
                cls_form = ClassManageForm(self, subject=cls)
                cls_form.data = request.POST
                cls_form.is_bound = True
                if cls_form.is_valid():
                    cls_form.save_data(cls)
                    return HttpResponseRedirect(request.get_full_path()) # Other forms may need updating, so just reload this view
            elif action == 'modify_sec':
                for sf in sec_forms:
                    if 'sec'+str(sf.index)+'-secid' in request.POST:
                        sf.data = request.POST
                        sf.is_bound = True
                        if sf.is_valid():
                            sec = ClassSection.objects.get(id=sf.cleaned_data['secid'])
                            orig_sec_status = sec.status
                            sf.save_data(sec)
                            verbs = RTC.getVisibleRegistrationTypeNames(prog)
                            # Kick all the students out of a class if it was rejected
                            if int(sec.status) < 0 and int(orig_sec_status) > 0:
                                for student in sec.students():
                                    sec.unpreregister_student(student, verbs)
                            return HttpResponseRedirect(request.get_full_path()) # Other forms may need updating, so just reload this view

        if self.program.program_modules.filter(handler='ClassFlagModule').exists():
            context['show_flags'] = True
            context['flag_types'] = ClassFlagType.get_flag_types(self.program)

        context['class'] = cls
        context['sections'] = sections
        context['cls_form'] = cls_form
        context['sec_forms'] = sec_forms
        context['cls_cancel_form'] = cls_cancel_form
        context['sec_cancel_forms'] = sec_cancel_forms
        context['module'] = self

        return render_to_response(self.baseDir()+'manageclass.html', request, context)

    @aux_call
    @needs_admin
    def approveclass(self, request, tl, one, two, module, extra, prog):
        cls = self.getClass(request, extra)
        cls.accept()
        if 'redirect' in request.GET:
            return HttpResponseRedirect(request.GET['redirect'])
        return HttpResponseRedirect(prog.get_manage_url() + 'manageclass/' + str(cls.id))

    @aux_call
    @needs_admin
    def rejectclass(self, request, tl, one, two, module, extra, prog):
        cls = self.getClass(request, extra)
        cls.reject()
        if 'redirect' in request.GET:
            return HttpResponseRedirect(request.GET['redirect'])
        return HttpResponseRedirect(prog.get_manage_url() + 'manageclass/' + str(cls.id))

    @aux_call
    @needs_admin
    def proposeclass(self, request, tl, one, two, module, extra, prog):
        cls = self.getClass(request, extra)
        cls.propose()
        if 'redirect' in request.GET:
            return HttpResponseRedirect(request.GET['redirect'])
        return HttpResponseRedirect(prog.get_manage_url() + 'manageclass/' + str(cls.id))

    @aux_call
    @needs_admin
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        cls.delete(True)
        return HttpResponseRedirect(prog.get_manage_url() + 'dashboard')

    @aux_call
    @needs_admin
    def coteachers(self, request, tl, one, two, module, extra, prog):
        from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule
        #   Allow submitting class ID via either GET or POST.
        if 'clsid' in request.GET:
            clsid = request.GET['clsid']
        elif 'clsid' in request.POST:
            clsid = request.POST['clsid']
        else:
            return self.goToCore(tl) # just fails.

        if extra == 'nojs':
            ajax = False
        else:
            ajax = True

        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})

        cls = classes[0]

        return TeacherClassRegModule.coteachers_logic(cls, request, prog, self.baseDir()+'coteachers.html', ajax, is_admin = True)

    @aux_call
    @needs_admin
    def editclass(self, request, tl, one, two, module, extra, prog):
        """ Hand over to the teacher class reg module so we only have this code in one place. """
        from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule

        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        if cls.category == self.program.open_class_category:
            action = 'editopenclass'
        else:
            action = 'edit'

        module_list = prog.getModules()
        for mod in module_list:
            if isinstance(mod, TeacherClassRegModule):
                return mod.makeaclass_logic(request,  tl, one, two, module, extra, prog, cls, action=action)

    @aux_call
    @needs_admin
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):
        # Search for teachers with names that start with search string
        if not 'name' in request.GET or 'name' in request.POST:
            return self.goToCore(tl)

        return TeacherClassRegModule.teacherlookup_logic(request, tl, one, two, module, extra, prog, newclass)

    @aux_call
    @needs_admin
    def classavailability(self, request, tl, one, two, module, extra, prog):
        """ Shows the collective availability of teachers for a class. """
        cls = self.getClass(request, extra)
        time_options = prog.getTimeSlots()
        time_groups = prog.getTimeGroups()

        teachers = cls.get_teachers()

        meeting_times = cls.all_meeting_times
        unscheduled_sections = []
        for section in cls.get_sections():
            if len(section.get_meeting_times()) == 0:
                unscheduled_sections.append(section)

        viable_times = []
        unavail_teachers = {}
        teaching_teachers = {}
        moderating_teachers = {}
        conflict_found = False
        for time in time_options:
            unavail_teachers[time] = []
            teaching_teachers[time] = []
            moderating_teachers[time] = []
            for teacher in teachers:
                if time not in teacher.getAvailableTimes(prog, True):
                    unavail_teachers[time].append(teacher)
                    if time in meeting_times:
                        conflict_found = True
                if time in teacher.getTaughtTimes(prog, exclude = [cls]):
                    teaching_teachers[time].append(teacher)
                if time in teacher.getModeratingTimesFromProgram(prog):
                    moderating_teachers[time].append(teacher)
            if (len(unavail_teachers[time]) + len(teaching_teachers[time]) + len(moderating_teachers[time])) == 0:
                viable_times.append(time)

        context =   {
                        'groups': [
                            [
                                {
                                    'available': t in viable_times,
                                    'slot': t,
                                    'id': t.id,
                                    'section': cls.get_section(t),
                                    'unavail_teachers': unavail_teachers.get(t),
                                    'teaching_teachers': teaching_teachers.get(t),
                                    'moderating_teachers': moderating_teachers.get(t),
                                }
                            for t in group]
                        for group in time_groups]
                    }
        context['class'] = cls
        context['unscheduled'] = unscheduled_sections
        context['conflict_found'] = conflict_found
        # this seems kinda hacky, but it's probably fine for now
        context['is_overbooked'] = sum([sec.duration for sec in cls.get_sections()]) > sum([Event.total_length(events).seconds/3600.0 for events in Event.group_contiguous(viable_times, int(Tag.getProgramTag('timeblock_contiguous_tolerance', program = prog)))])
        context['num_groups'] = len(context['groups'])
        context['program'] = prog

        return render_to_response(self.baseDir()+'classavailability.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

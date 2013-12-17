
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
from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call, aux_call, meets_deadline, needs_student, meets_grade
from esp.program.modules         import module_ext
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories, StudentRegistration, RegistrationType
from esp.program.views           import lottery_student_reg, lsr_submit as lsr_view_submit
from esp.datatree.models         import *
from esp.web.util                import render_to_response
from django                      import forms
from django.http                 import HttpResponseRedirect, HttpResponse
from django.template.loader      import render_to_string
from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserBit, UserAvailability, Record
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
from esp.datatree.models         import DataTree
from datetime                    import datetime, timedelta
from django.utils                import simplejson
from collections                 import defaultdict
from esp.cache                   import cache_function
from uuid                        import uuid4 as get_uuid
from django.db.models.query      import Q
from django.views.decorators.cache import cache_control
from esp.middleware.threadlocalrequest import get_current_request
from django.core.exceptions      import ObjectDoesNotExist
    
class StudentRegPhase2(ProgramModuleObj):

    def students(self, QObject = False):
        # TODO: fill this in
        q = Q()
        if QObject:
            return {'phase2_students': q}
        else:
            return {'phase2_students': ESPUser.objects.filter(q).distinct()}

    def studentDesc(self):
        return {'phase2_students': "Students who have completed student registration phase 2"}

    def isCompleted(self):
        records = Record.objects.filter(user=self.user, event="reg_phase2_done",
                                        program=self.program)
        return records.count() != 0

    def deadline_met(self, extension=None):
        #   Allow default extension to be overridden if necessary
        if extension is not None:
            return super(StudentClassRegModule, self).deadline_met(extension)
        else:
            return super(StudentClassRegModule, self).deadline_met('/Classes/Lottery')

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Registration Phase 2",
            "admin_title": "Student Registration Phase 2",
            "module_type": "learn",
            "seq": 6
            }

        """ def prepare(self, context={}):
        if context is None: context = {}

        context['schedulingmodule'] = self 
        return context """

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def studentreg_2(self, request, tl, one, two, module, extra, prog):
        """
        Serve the phase 2 student reg page. The page lists the timeslots of the
        program with the associated Priority/N classes for each one, and a link
        to edit the timeslot priorities of each timeslot.
        """

        timeslot_dict = {}
        # Populate the timeslot dictionary with the priority to class title
        # mappings for each timeslot.
        priority_regs = StudentRegistration.valid_objects().filter(
            user=request.user, relationship__name__startswith='Priority')
        priority_regs = priority_regs.values(
            'relationship__name', 'section', 'section__parent_class__title')
        for student_reg in priority_regs:
            rel = student_reg['relationship__name']
            title = student_reg['section__parent_class__title']
            sec = ClassSection.objects.get(pk=student_reg['section'])
            times = sec.meeting_times.all().order_by('start')
            if times.count() == 0:
                continue
            timeslot = times[0].id
            if not timeslot in timeslot_dict:
                timeslot_dict[timeslot] = {rel: title}
            else:
                timeslot_dict[timeslot][rel] = title

        # Iterate through timeslots and create a list of tuples of information
        prevTimeSlot = None
        blockCount = 0
        schedule = []
        timeslots = prog.getTimeSlots(types=['Class Time Block', 'Compulsory'])
        for i in range(len(timeslots)):
            timeslot = timeslots[i]
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1

            if timeslot.id in timeslot_dict:
                priority_dict = timeslot_dict[timeslot.id]
                priority_list = sorted(priority_dict.items())
                schedule.append((timeslot, priority_list, blockCount + 1))
            else:
                schedule.append((timeslot, {}, blockCount + 1))

            prevTimeSlot = timeslot

        context = {}
        context['timeslots'] = schedule
        context['one'] = one
        context['two'] = two
        context['prog'] = prog
        return render_to_response(
            self.baseDir()+'studentregphase2.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    def complete_studentreg_2(self, request, tl, one, two, module, extra, prog):
        """
        Set a Record for the user indicating that phase 2 is complete.
        """
        records = Record.objects.filter(user=request.user,
                                        event="reg_phase2_done", program=prog)
        if records.count() == 0:
            Record.objects.create(user=request.user,
                                  event="reg_phase2_done", program=prog)

        return HttpResponseRedirect('/%s/%s/%s/studentreg' % (tl, one, two))

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def timeslot_priorities(self, request, tl, one, two, module, extra, prog):
        """
        Serve a phase-2 specific catalog, which displays only class subejcts
        for which the student has a StudentSubjectInterest. The sticky on top
        of the catalog lets the student order the top N priorities of classes
        for this particular timeslot. The timeslot is specified through extra.
        """
        timeslot = Event.objects.get(pk=int(extra), program=prog)
        context = dict()
        context['timeslot'] = timeslot.id
        context['num_priorities'] = prog.priorityLimit()
        context['priorities'] = range(1,prog.priorityLimit()+1)
        return render_to_response(
            'program/modules/studentregphase2/catalog_phase2.html',
            request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def save_priorities(self, request, tl, one, two, module, extra, prog):
        """
        Saves the priority preferences for student registration phase 2.
        """
        data = simplejson.loads(request.POST['json_data']);
        timeslot_id = data.keys()[0]
        priorities = data[timeslot_id]
        rel_names = ['Priority/%s'%p for p in priorities.keys()]
        # Pull up the registrations that exist (including expired ones)
        srs = StudentRegistration.objects.filter(
            user=request.user, section__parent_class__parent_program=prog,
            relationship__name__in=rel_names,
            section__meeting_times__id__exact=timeslot_id)
        srs = srs.order_by('relationship__name')
        # Modify the existing registrations as needed to ensure the section
        # is correct, and they are unexpired
        for (sr, p) in zip(srs, sorted(priorities.keys())):
            # If blank, we are removing priority
            if priorities[p] == '':
                sr.expire()
                continue
            sec_id = int(priorities[p])

            should_save = False
            if sr.section.id != sec_id:
                sr.section = ClassSection.objects.get(
                    parent_class=sec_id,
                    meeting_times__id__exact=timeslot_id)
                should_save = True
            if not sr.is_valid():
                sr.unexpire(save=False)
                should_save = True
            if should_save:
                sr.save()
        # Create registrations that need to be created
        rel_existing_names = srs.values_list('relationship__name', flat=True)
        rel_existing = [r.split('/')[1]
                        for r in rel_existing_names]
        rel_create = set(priorities.keys()) - set(rel_existing)
        for rel_index in rel_create:
            rel, created = RegistrationType.objects.get_or_create(
                name='Priority/%s' % rel_index)
            try:
                sec = ClassSection.objects.get(
                    parent_class=int(priorities[rel_index]),
                    meeting_times__id__exact=timeslot_id)
            except ValueError as e:
                # Catch having an empty string for the priority
                # (nothing selected)
                continue
            except ObjectDoesNotExist as e:
                print 'ObjectDoesNotExist', e
                continue
            sr = StudentRegistration(
                user=request.user,
                section=sec,
                relationship=rel)
            sr.save()

        return HttpResponse()


    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def save_preferences(self, request, tl, one, two, module, extra, prog):

        data = json.loads(request.POST['json_data'])
        return lsr_submit_HSSP(request, self.program, self.program.priority_limit, data)

    @aux_call
    @cache_control(public=True, max_age=3600)
    def timeslots_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program timeslot names for the tabs in the lottery inteface """
        # using .extra() to select all the category text simultaneously
        ordered_timeslots = sorted(self.program.getTimeSlotList(), key=lambda event: event.start)
        ordered_timeslot_names = list()
        for item in ordered_timeslots:
            ordered_timeslot_names.append([item.id, item.short_description])

        resp = HttpResponse(mimetype='application/json')
        
        simplejson.dump(ordered_timeslot_names, resp)
        
        return resp


    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery/View')
    def viewlotteryprefs(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['student'] = request.user
        context['program'] = prog

        priority_classids = set()
        uniquified_flags = []
        priority_flags = StudentRegistration.valid_objects().filter(user=request.user, section__parent_class__parent_program=prog, relationship__name='Priority/1')
        for flag in priority_flags:
            if flag.section.id not in priority_classids:
                priority_classids.add(flag.section.id)
                uniquified_flags.append(flag)
        context['priority'] = uniquified_flags
        if priority_flags.count() == 0:
            context['pempty'] = True
        else: context['pempty'] = False

        interested_classids = set()
        uniquified_interested = []
        interested = StudentRegistration.valid_objects().filter(user=request.user, section__parent_class__parent_program=prog, relationship__name='Interested')
        for flag in interested:
            if flag.section.id not in interested_classids:
                interested_classids.add(flag.section.id)
                uniquified_interested.append(flag)
        context['interested' ] = uniquified_interested
        if interested.count() == 0:
            context['iempty'] = True
        else: context['iempty'] = False

        return render_to_response(self.baseDir()+'view_lottery_prefs.html', request, context, prog=prog)
    
    class Meta:
        abstract = True


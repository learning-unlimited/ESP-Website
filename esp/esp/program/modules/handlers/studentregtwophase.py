__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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

import datetime
import json
import logging
logger = logging.getLogger(__name__)

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Min, Q
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, Http404

from esp.cal.models import Event
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.models import ClassCategories, ClassSection, ClassSubject, RegistrationType, StudentRegistration, StudentSubjectInterest
from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, meets_deadline, needs_student, meets_grade, meets_cap, no_auth
from esp.users.models import Record, ESPUser
from esp.tagdict.models import Tag
from esp.utils.web import render_to_response
from esp.utils.query_utils import nest_Q

class StudentRegTwoPhase(ProgramModuleObj):

    def students(self, QObject = False):
        q_sr = Q(studentregistration__section__parent_class__parent_program=self.program) & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')
        q_ssi = Q(studentsubjectinterest__subject__parent_program=self.program) & nest_Q(StudentSubjectInterest.is_valid_qobject(), 'studentsubjectinterest')
        if QObject:
            return {'twophase_star_students': q_ssi,
                    'twophase_priority_students' : q_sr}
        else:
            return {'twophase_star_students': ESPUser.objects.filter(q_ssi).distinct(),
                    'twophase_priority_students': ESPUser.objects.filter(q_sr).distinct()}

    def studentDesc(self):
        return {'twophase_star_students': "Students who have starred classes in the two-phase lottery",
                'twophase_priority_students': "Students who have marked choices in the two-phase lottery"}

    def isCompleted(self):
        records = Record.objects.filter(user=get_current_request().user,
                                        event="twophase_reg_done",
                                        program=self.program)
        return records.count() != 0

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Two-Phase Student Registration",
            "admin_title": "Two-Phase Student Registration",
            "module_type": "learn",
            "seq": 3,
            "required": True,
            "choosable": 0,
            }

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    @meets_cap
    def studentreg2phase(self, request, tl, one, two, module, extra, prog):
        """
        Serves the two-phase student reg page. This page includes instructions
        for registration, and links to the phase1/phase2 sub-pages.
        """

        context = {}
        timeslot_dict = {}
        # Populate the timeslot dictionary with the priority to class title
        # mappings for each timeslot.
        priority_regs = StudentRegistration.valid_objects().filter(
            user=request.user, relationship__name__startswith='Priority')
        priority_regs = priority_regs.select_related(
            'relationship', 'section', 'section__parent_class')
        for student_reg in priority_regs:
            rel = student_reg.relationship.name
            title = student_reg.section.parent_class.title
            sec = student_reg.section
            times = sec.meeting_times.all().order_by('start')
            if times.count() == 0:
                continue
            timeslot = times[0].id
            if not timeslot in timeslot_dict:
                timeslot_dict[timeslot] = {rel: title}
            else:
                timeslot_dict[timeslot][rel] = title

        star_counts = {}
        interests = StudentSubjectInterest.valid_objects().filter(
            user=request.user, subject__parent_program=prog)
        interests = interests.select_related(
            'subject').prefetch_related('subject__sections__meeting_times')
        for interest in interests:
            cls = interest.subject
            for sec in cls.sections.all():
                times = sec.meeting_times.all()
                if len(times) == 0:
                    continue
                timeslot = min(times, key=lambda t: t.start).id
                if not timeslot in star_counts:
                    star_counts[timeslot] = 1
                else:
                    star_counts[timeslot] += 1

        # Iterate through timeslots and create a list of tuples of information
        prevTimeSlot = None
        blockCount = 0
        schedule = []
        timeslots = prog.getTimeSlots(types=['Class Time Block', 'Compulsory'])

        context['num_priority'] = prog.priorityLimit()
        context['num_star'] = int(Tag.getProgramTag("num_stars", program = prog))

        for i in range(len(timeslots)):
            timeslot = timeslots[i]
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1

            if timeslot.id in timeslot_dict:
                priority_dict = timeslot_dict[timeslot.id]
            else:
                priority_dict = {}
            temp_list = []
            for i in range(1, context['num_priority'] + 1):
                priority_name = 'Priority/%s' % i
                reg_type, created = RegistrationType.objects.get_or_create(name = priority_name, category = "student")
                if priority_name in priority_dict:
                    temp_list.append((reg_type, priority_dict[priority_name]))
                else:
                    temp_list.append((reg_type, ""))
            priority_list = temp_list
            star_count = 0
            if timeslot.id in star_counts:
                star_count = star_counts[timeslot.id]
            schedule.append((timeslot, priority_list, blockCount + 1, star_count, float(star_count)/context['num_star']*100))

            prevTimeSlot = timeslot

        context['timeslots'] = schedule

        return render_to_response(
            self.baseDir()+'studentregtwophase.html', request, context)

    def catalog_context(self, request, tl, one, two, module, extra, prog):
        """
        Builds context specific to the catalog. Used by all views which render
        the catalog. This is not a view in itself.
        """
        context = {}
        # FIXME(gkanwar): This is a terrible hack, we should find a better way
        # to filter out certain categories of classes
        context['open_class_category_id'] = prog.open_class_category.id
        try:
            lunch_category = ClassCategories.objects.get(category='Lunch')
            context['lunch_category_id'] = lunch_category.id
        except ClassCategories.DoesNotExist:
            context['lunch_category_id'] = -1
        return context

    @aux_call
    @no_auth
    def view_classes(self, request, tl, one, two, module, extra, prog):
        """
        Displays a filterable catalog that anyone can view.
        """
        # get choices for filtering options
        context = {}

        def group_columns(items):
            # collect into groups of 5
            cols = []
            for i, item in enumerate(items):
                if i % 5 == 0:
                    col = []
                    cols.append(col)
                col.append(item)
            return cols

        category_choices = []
        for category in prog.class_categories.all():
            # FIXME(gkanwar): Make this less hacky, once #770 is resolved
            if category.category == 'Lunch':
                continue
            category_choices.append((category.id, category.category))
        context['category_choices'] = group_columns(category_choices)

        grade_choices = []
        grade_choices.append(('ALL', 'All'))
        for grade in range(prog.grade_min, prog.grade_max + 1):
            grade_choices.append((grade, grade))
        context['grade_choices'] = group_columns(grade_choices)

        catalog_context = self.catalog_context(
            request, tl, one, two,module, extra, prog)
        context.update(catalog_context)

        return render_to_response(self.baseDir() + 'view_classes.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    @meets_cap
    def mark_classes(self, request, tl, one, two, module, extra, prog):
        """
        Displays a filterable catalog which allows starring classes that the
        user is interested in.
        """
        # get choices for filtering options
        context = {}

        def group_columns(items):
            # collect into groups of 5
            cols = []
            for i, item in enumerate(items):
                if i % 5 == 0:
                    col = []
                    cols.append(col)
                col.append(item)
            return cols

        category_choices = []
        for category in prog.class_categories.all():
            # FIXME(gkanwar): Make this less hacky, once #770 is resolved
            if category.category == 'Lunch':
                continue
            category_choices.append((category.id, category.category))
        context['category_choices'] = group_columns(category_choices)

        catalog_context = self.catalog_context(
            request, tl, one, two,module, extra, prog)
        context.update(catalog_context)

        return render_to_response(self.baseDir() + 'mark_classes.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    @meets_cap
    def mark_classes_interested(self, request, tl, one, two, module, extra, prog):
        """
        Saves the set of classes marked as interested by the student.

        Ex: request.POST['json_data'] = {
            'interested': [1,5,3,9],
            'not_interested': [4,6,10]
        }
        """
        if not 'json_data' in request.POST:
            return HttpResponseBadRequest('JSON data not included in request.')
        try:
            json_data = json.loads(request.POST['json_data'])
        except ValueError:
            return HttpResponseBadRequest('JSON data mis-formatted.')
        if not isinstance(json_data.get('interested'), list) or \
           not isinstance(json_data.get('not_interested'), list):
            return HttpResponseBadRequest('JSON data mis-formatted.')

        # Determine which of the given class ids are valid
        valid_classes = ClassSubject.objects.filter(
            pk__in=json_data['interested'],
            parent_program=prog,
            status__gte=0,
            grade_min__lte=request.user.getGrade(prog),
            grade_max__gte=request.user.getGrade(prog))
        # Unexpire any matching SSIs that exist already (to avoid
        # creating duplicate objects).
        to_unexpire = StudentSubjectInterest.objects.filter(
            user=request.user,
            subject__in=valid_classes)
        to_unexpire.update(end_date=None)
        # Determine which valid ids haven't had SSIs created yet
        # and bulk create those objects.
        valid_ids = valid_classes.values_list('pk', flat=True)
        existing_ids = to_unexpire.values_list('subject__pk', flat=True)
        to_create_ids = set(valid_ids) - set(existing_ids)
        StudentSubjectInterest.objects.bulk_create([
            StudentSubjectInterest(
                user=request.user,
                subject_id=subj_id)
            for subj_id in to_create_ids])
        # Expire any matching SSIs that are in 'not_interested'
        to_expire = StudentSubjectInterest.objects.filter(
            user=request.user,
            subject__pk__in=json_data['not_interested'])
        to_expire.update(end_date=datetime.datetime.now())

        if request.is_ajax():
            return HttpResponse()
        else:
            return self.goToCore(tl)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    @meets_cap
    def rank_classes(self, request, tl, one, two, module, extra, prog):
        """
        Displays a filterable catalog including only class subjects for which
        the student has a StudentSubjectInterest. The sticky on top
        of the catalog lets the student order the top N priorities of classes
        for this particular timeslot. The timeslot is specified through extra.
        """
        try:
            timeslot = Event.objects.get(pk=int(extra), program=prog)
        except (TypeError, ValueError, Event.DoesNotExist) as e:
            raise Http404
        context = dict()
        context['timeslot'] = timeslot
        context['num_priorities'] = prog.priorityLimit()
        context['priorities'] = []
        for rel_index in range(1, prog.priorityLimit()+1):
            rel_name = 'Priority/%s' % rel_index
            rel, created = RegistrationType.objects.get_or_create(
                name=rel_name, category='student')
            context['priorities'].append((rel_index, rel))

        catalog_context = self.catalog_context(
            request, tl, one, two,module, extra, prog)
        context.update(catalog_context)

        return render_to_response(
            self.baseDir() + 'rank_classes.html', request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    @meets_cap
    def save_priorities(self, request, tl, one, two, module, extra, prog):
        """
        Saves the priority preferences for student registration phase 2.
        """
        if not 'json_data' in request.POST:
            return HttpResponseBadRequest('JSON data not included in request.')
        try:
            json_data = json.loads(request.POST['json_data'])
        except ValueError:
            return HttpResponseBadRequest('JSON data mis-formatted.')
        try:
            [timeslot_id] = json_data.keys()
        except ValueError:
            return HttpResponseBadRequest('JSON data mis-formatted.')
        if not isinstance(json_data[timeslot_id], dict):
            return HttpResponseBadRequest('JSON data mis-formatted.')

        timeslot = Event.objects.get(pk=timeslot_id)
        priorities = json_data[timeslot_id]
        for rel_index, cls_id in priorities.items():
            rel_name = 'Priority/%s' % rel_index
            rel = RegistrationType.objects.get(name=rel_name, category='student')

            # Pull up any registrations that exist (including expired ones)
            srs = StudentRegistration.objects.annotate(
                Min('section__meeting_times__start'))
            srs = srs.filter(
                user=request.user,
                section__parent_class__parent_program=prog,
                section__meeting_times__start__min=timeslot.start,
                relationship=rel)

            if cls_id == '':
                # Blank: nothing selected, expire existing registrations
                for sr in srs:
                    sr.expire()
                continue

            cls_id = int(cls_id)
            sec = ClassSection.objects.annotate(Min('meeting_times__start'))
            try:
                sec = sec.get(parent_class=cls_id,
                              parent_class__parent_program=prog,
                              meeting_times__start__min=timeslot.start)
            except (ClassSection.DoesNotExist,
                    ClassSection.MultipleObjectsReturned):
                # XXX: what if a class has multiple sections in a timeblock?
                logger.warning("Could not save priority for class %s in "
                               "timeblock %s", cls_id, timeslot_id)
                continue
            # sanity checks
            if (not sec.status > 0 or not sec.parent_class.status > 0):
                logger.warning("Class '%s' was not approved.  Not letting "
                               "user '%s' register.", sec, request.user)
            if (not sec.parent_class.grade_min <= request.user.getGrade(prog)
                or not sec.parent_class.grade_max >= request.user.getGrade(prog)):
                logger.warning("User '%s' not in class grade range; not "
                               "letting them register.", request.user)
                continue

            if not srs.exists():
                # Create a new registration
                sr = StudentRegistration(
                    user=request.user,
                    relationship=rel)
            else:
                # Pull the first StudentRegistration, expire the others
                for sr in srs[1:]:
                    sr.expire()
                sr = srs[0]

            # Modify as needed to ensure the section is correct and
            # expiration date is valid
            if sr.section_id is None or sr.section.parent_class.id != cls_id:
                sr.section = sec
            sr.unexpire(save=False)
            sr.save()

        return self.goToCore(tl)

    class Meta:
        proxy = True
        app_label = 'modules'

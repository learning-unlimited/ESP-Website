from __future__ import absolute_import
from __future__ import division
from django.http import HttpResponse
from esp.program.models import Program, ClassSection, ClassSubject, ModeratorRecord
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.resources.models import ResourceRequest
from copy import deepcopy
from esp.cal.models import *
from datetime import date
from esp.utils.web import render_to_response
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.cal.models import Event

from esp.middleware.threadlocalrequest import get_current_request

import json
import re
import six
from six.moves import map
from six.moves import range


class SchedulingCheckModule(ProgramModuleObj):
    doc = """Provides diagnostics to check for invalid class schedule assignments."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Scheduling Diagnostics",
            "link_title": "Run Scheduling Diagnostics",
            "module_type": "manage",
            "seq": 10,
            "choosable": 1,
            }

    @main_call
    @needs_admin
    def scheduling_checks(self, request, tl, one, two, module, extra, prog):
        s = SchedulingCheckRunner(prog)
        if extra:
            results = s.run_diagnostics([extra])
            return HttpResponse(results)
        else:
            context = {'check_list': s.all_diagnostics(), 'unreviewed': "unreviewed" in request.GET}
            return render_to_response(self.baseDir()+'output.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

#For formatting output.  The default is to use JSONFormatter, but someone writing a script
#may want to use RawSCFormatter to get the original data structures
class RawSCFormatter:
    def format_table(self, l, options={}, help_text=""):
        return l

    def format_list(self, l, options={}, help_text=""):
        return l

# Builds JSON output for an object with attributes help_text, headings, and body.
class JSONFormatter:
    #requires: d, a two level dictionary where the the first set of
    #   keys are the headings expected on the side of the table, and
    #   the second set are the headings expected on the top of the table
    def format_table(self, d, options={}, help_text=""):
        if isinstance(d, list):
            return json.dumps(self._format_list_table(d, options['headings'], help_text=help_text))
        else:
            return json.dumps(self._format_dict_table(d, options['headings'], help_text=help_text))

    def format_list(self, l, heading="", help_text=""): # needs verify
        output = {}
        output["help_text"] = help_text
        output["headings"] = list(map(str, heading)) # no headings

        # might be redundant, but it makes sure things aren't in a weird format
        output["body"] = [self._table_row([row]) for row in l]
        return json.dumps(output)


    def _table_row(self, row):
        next_row = []
        for r in row:
            #displaying lists is sometimes borked.  This makes it not borked
            if isinstance(r, list):
                r = [str(i) for i in r]
            if isinstance(r, int):
                next_row.append(r)
            else:
                next_row.append(str(r))
        return next_row

    def _format_list_table(self, d, headings, help_text=""): #needs verify
        output = {}
        output["help_text"] = help_text
        output["headings"] = list(map(str, headings))
        output["body"] = [self._table_row([row[h] for h in headings]) for row in d]
        return output

    def _format_dict_table(self, d, headings, help_text=""): #needs verify
        headings = [""] + headings[:]
        output = {}
        output["help_text"] = help_text
        output["headings"] = list(map(str, headings))
        output["body"] = [self._table_row([key] + [row[h] for h in headings if h]) for key, row in sorted(six.iteritems(d))]
        return output

class SchedulingCheckRunner:
    # Generate html report and generate text report functions?lingCheckRunner:
    def __init__(self, program, formatter=JSONFormatter()):
        """
        high_school_only and lunch should be lists of indeces of timeslots for the high school
        only block and for lunch respectively
        """
        self.p = program
        self.formatter = formatter

        request = get_current_request()
        self.incl_unreview = "unreviewed" in request.GET

        self.lunch_blocks = self._getLunchByDay()

        #things that we'll calculate lazilly
        self.listed_sections = False
        self.listed_nonwalkins = False
        self.calculated_classes_missing_resources = False
        self.d_categories = []
        self.d_grades = []

    def _getLunchByDay(self):
        #   Get IDs of timeslots allocated to lunch by day
        #   (note: requires that this is constant across days)
        lunch_timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=self.p, meeting_times__parent_class__category__category='Lunch').order_by('start').distinct()
        #   Note: this code should not be necessary once lunch-constraints branch is merged (provides Program.dates())
        dates = []
        for ts in self.p.getTimeSlots():
            ts_day = date(ts.start.year, ts.start.month, ts.start.day)
            if ts_day not in dates:
                dates.append(ts_day)
        lunch_by_day = [[] for x in dates]
        for ts in lunch_timeslots:
            d = date(ts.start.year, ts.start.month, ts.start.day)
            lunch_by_day[dates.index(d)].append(ts)
        return lunch_by_day

    def run_diagnostics(self, diagnostics=None):
        if diagnostics is None:
             diagnostics = self.all_diagnostics()
        return [getattr(self, diag)() for diag in diagnostics]

    # Update this to add a scheduling check.
    def all_diagnostics(self):
        if self.p.hasModule("TeacherModeratorModule"):
            two_classes_name = 'Teachers/' + self.p.getModeratorTitle().capitalize() + 's handling two classes at once'
        else:
            two_classes_name = 'Teachers teaching two classes at once'
        diags = [
            #Block Diagnostics
            ('lunch_blocks_setup', 'Lunch blocks'),
            ('inconsistent_rooms_and_times', 'Mismatched rooms and meeting times'),
            ('special_classroom_types', 'Special classroom types'),
            ('room_capacity_mismatch', 'Class max size/room max size mismatches'),
            #Class Diagnostiscs
            ('wrong_classroom_type', 'Classes in wrong classroom type'),
            ('classes_missing_resources', 'Unfulfilled resource requests'),
            ('missing_resources_by_hour', 'Unfulfilled resource requests by hour'),
            ('incompletely_scheduled_classes', 'Classes not completely scheduled or with gaps'),
            ('classes_which_cover_lunch', 'Classes which are scheduled over lunch'),
            ('classes_wrong_length', 'Classes which are the wrong length'),
            ('no_overlap_classes', "Classes which shouldn't overlap"),
            ('unapproved_scheduled_classes', 'Classes which are scheduled but not approved'),
            #Teacher Diagnostics
            ('teachers_unavailable', "Teachers teaching when they aren't available"),
            ('teachers_teaching_two_classes_same_time', two_classes_name),
            ('teachers_who_like_running', 'Teachers who like running'),
            ('hungry_teachers', 'Hungry teachers'),
            ('inflexible_teachers', 'Teachers with limited flexibility'),
            #Information Diagnostics
            ('classes_by_category', 'Number of classes in each block by category'),
            ('capacity_by_category', 'Total capacity in each block by category'),
            ('classes_by_grade', 'Number of classes in each block by grade'),
            ('capacity_by_grade', 'Total capacity in each block by grade'),
            ('admins_teaching_per_timeblock', 'Admins teaching per timeslot'),
            ('multiple_classes_same_resource_same_time', 'Double-booked resources')
        ]
        if self.p.hasModule("TeacherModeratorModule"):
            diags.extend([
                ('unavailable_moderators', self.p.getModeratorTitle().capitalize() + "s helping when they aren't available"),
                ('mismatched_moderators', self.p.getModeratorTitle().capitalize() + 's with category mismatches'),
            ])
        return diags

    #################################################
    #
    #    Useful functions
    #
    #################################################

    def _timeslot_dict(self, slot=lambda: 0):
        d = {}
        for i in self.p.getTimeSlotList():
            d[i] = slot()
        return d

    #memoize the list of all class sections in this program
    def _all_class_sections(self, include_walkins=True):
        if include_walkins and self.listed_sections:
            return self.all_sections
        elif (include_walkins == False) and self.listed_nonwalkins:
            return self.all_nonwalkins
        else:
            qs = self.p.sections()
            if include_walkins == False:
                #filter out walkins
                qs = qs.exclude(parent_class__category__id=self.p.open_class_category.id)
            if self.incl_unreview:
                #filter out rejected/cancelled sections
                qs = qs.exclude(status__lt=0)
            else:
                #filter out non-approved
                qs = qs.exclude(status__lte=0)
            #filter out unscheduled classes
            qs = qs.exclude(resourceassignment__isnull=True)
            #filter out lunch
            qs = qs.exclude(parent_class__category__category=u'Lunch')
            qs = qs.select_related('parent_class', 'parent_class__parent_program', 'parent_class__category')
            qs = qs.prefetch_related('meeting_times', 'resourceassignment_set', 'resourceassignment_set__resource', 'parent_class__teachers', 'moderators')
            if include_walkins:
                self.all_sections = list(qs)
                self.listed_sections = True
                return self.all_sections
            else:
                self.all_nonwalkins = list(qs)
                self.listed_nonwalkins = True
                return self.all_nonwalkins

    #################################################
    #
    #    Diagnostic functions
    #
    #################################################
    def lunch_blocks_setup(self):
        lunch_block_strings = []
        for lunch_block_list in self.lunch_blocks:
            for l in lunch_block_list:
                lunch_block_strings.append(str(l))
        return self.formatter.format_list(lunch_block_strings, ["Lunch Blocks"])

    def incompletely_scheduled_classes(self):
        problem_classes = []
        for s in self._all_class_sections():
            mt =  sorted(s.get_meeting_times())
            rooms = [a.resource for a in s.classroomassignments()]
            if(len(rooms) != len(mt)):
                problem_classes.append(s)
            else:
                for i in range(0, len(mt) - 1):
                    if not Event.contiguous(mt[i], mt[i+1]):
                        problem_classes.append(s)
        return self.formatter.format_list(problem_classes, ["Classes"])

    def inconsistent_rooms_and_times(self):
        output = []
        for s in self._all_class_sections():
            mt = sorted(s.get_meeting_times())
            rooms = [a.resource for a in s.classroomassignments()]
            res_events = sorted([x.event for x in rooms])
            if res_events != mt:
                output.append({"Section": s, "Resource events": res_events,
                               "Meeting times": mt})
        return self.formatter.format_table(output,
            {"headings": ["Section", "Resource events", "Meeting times"]})

    def classes_which_cover_lunch(self):
        l = []
        for s in self._all_class_sections(include_walkins=False):
            mt =  s.get_meeting_times()
            for lunch in self.lunch_blocks:
                if len(lunch) == 0:
                    pass
                elif not (False in [b in mt for b in lunch]):
                    l.append(s)
        return self.formatter.format_list(l, ["Classes"])

    def classes_wrong_length(self):
        output = []
        for sec in self._all_class_sections():
            start_time = sec.start_time_prefetchable()
            end_time = sec.end_time_prefetchable()
            length = end_time - start_time
            if abs(round(length.total_seconds() / 3600.0, 2) - float(sec.duration)) > 0.0:
                output.append(sec)
        return self.formatter.format_list(output, ["Classes"])

    def unavailable_moderators(self):
        """
        Moderators who are moderating at a time at which they are not available.
        """
        l = []
        for s in self._all_class_sections():
            for m in s.get_moderators():
                available = m.getAvailableTimes(s.parent_program, ignore_classes=True, ignore_moderation=True)
                for e in s.get_meeting_times():
                    if e not in available:
                        l.append({self.p.getModeratorTitle(): m, "Time": e, "Section": s})
        return self.formatter.format_table(l, {"headings": ["Section", self.p.getModeratorTitle(), "Time"]})

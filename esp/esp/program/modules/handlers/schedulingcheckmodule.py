from django.http import HttpResponse
from esp.program.models import ClassCategories, ClassSection, ModeratorRecord
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.program.modules.admin_search import AdminSearchEntry, SEARCH_CATEGORY_CLASSES
from esp.resources.models import Resource, ResourceRequest
from copy import deepcopy
from esp.cal.models import *
from datetime import date
from collections import defaultdict
from esp.utils.web import render_to_response
from esp.tagdict.models import Tag
from esp.cal.models import Event

from esp.middleware.threadlocalrequest import get_current_request

import json
import re


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

    @classmethod
    def get_admin_search_entry(cls, program, tl, view_name, pmo):
        # Surface the scheduling diagnostics page in the admin dashboard search dropdown.
        if view_name != "scheduling_checks":
            return None
        return AdminSearchEntry(
            id="manage_%s" % view_name,
            url="/%s/%s/%s" % (tl, program.getUrlBase(), view_name),
            title="Scheduling Diagnostics",
            category=SEARCH_CATEGORY_CLASSES,
            keywords=["scheduling", "diagnostics", "checks", "schedule", "conflicts"],
        )

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
        output["body"] = [self._table_row([key] + [row[h] for h in headings if h]) for key, row in sorted(d.items())]
        return output

class SchedulingCheckRunner:
    # Generate html report and generate text report functions?lingCheckRunner:
    def __init__(self, program, formatter=JSONFormatter()):
        """
        high_school_only and lunch should be lists of indices of timeslots for the high school
        only block and for lunch respectively
        """
        self.p = program
        self.formatter = formatter

        request = get_current_request()
        self.incl_unreview = bool(request and "unreviewed" in request.GET)

        self.lunch_blocks = self._getLunchByDay()

        #things that we'll calculate lazilly
        self.built_snapshot = False
        self.calculated_classes_missing_resources = False
        self.d_categories = []
        self.d_grades = []
        #   Availability is expensive to compute; memoize it per user so that
        #   it is both fast and stable for the duration of this run.
        self._available_times_by_user = {}

    def _getLunchByDay(self):
        #   Get IDs of timeslots allocated to lunch by day
        #   (note: requires that this is constant across days)
        lunch_timeslots = self.p.lunch_timeslots()
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
                ('moderator_movement_dependency_loops', self.p.getModeratorTitle().capitalize() + ' movement dependency loops'),
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

    def _build_snapshot(self):
        """Load every section and its scheduling data once, up front.

        Diagnostics used to re-query meeting times, rooms, teachers and
        moderators as they iterated. If someone rescheduled a class mid-run,
        those queries returned different data each time, so checks disagreed
        with each other and indexing into a now-empty result blew up
        (see issue #511). Everything below is read exactly once and then
        served from memory, so a run sees a single consistent schedule.
        """
        if self.built_snapshot:
            return

        qs = self.p.sections()
        if self.incl_unreview:
            #filter out rejected/cancelled sections
            qs = qs.exclude(status__lt=0)
        else:
            #filter out non-approved
            qs = qs.exclude(status__lte=0)
        #filter out unscheduled classes
        qs = qs.exclude(resourceassignment__isnull=True)
        #filter out lunch
        qs = qs.exclude(parent_class__category__is_lunch=True)
        qs = qs.select_related('parent_class', 'parent_class__parent_program', 'parent_class__category')
        qs = qs.prefetch_related('meeting_times', 'resourceassignment_set',
                                 'resourceassignment_set__resource',
                                 'resourceassignment_set__resource__res_type',
                                 'resourceassignment_set__resource__event',
                                 'resourcerequest_set', 'resourcerequest_set__res_type',
                                 'parent_class__teachers', 'moderators')

        self.all_sections = list(qs)
        open_class_category_id = self.p.open_class_category.id
        self.all_nonwalkins = [s for s in self.all_sections
                               if s.parent_class.category_id != open_class_category_id]

        self._meeting_times = {}
        self._resources = {}
        self._classrooms = {}
        self._classroom_by_time = {}
        self._teachers = {}
        self._moderators = {}
        self._requests = {}
        self._sections_by_teacher = defaultdict(list)
        self._sections_by_class = defaultdict(list)

        for section in self.all_sections:
            meeting_times = sorted(section.meeting_times.all(), key=lambda event: event.start)
            resources = [a.resource for a in section.resourceassignment_set.all()]
            #   Order rooms by timeslot so that classrooms[0] is the room the
            #   section starts in rather than whatever the database returned first.
            classrooms = sorted((r for r in resources if r.res_type.name == 'Classroom'),
                                key=lambda room: (room.event.start, room.id))
            teachers = list(section.parent_class.teachers.all())

            self._meeting_times[section.id] = meeting_times
            self._resources[section.id] = resources
            self._classrooms[section.id] = classrooms
            self._classroom_by_time[section.id] = {room.event_id: room for room in classrooms}
            self._teachers[section.id] = teachers
            self._moderators[section.id] = list(section.moderators.all())
            self._requests[section.id] = list(section.resourcerequest_set.all())

            for teacher in teachers:
                self._sections_by_teacher[teacher].append(section)
            self._sections_by_class[section.parent_class_id].append(section)

        self._build_furnishings_snapshot()
        self._moderator_categories = {
            record.user_id: list(record.class_categories.all())
            for record in ModeratorRecord.objects.filter(program=self.p)
                                                 .prefetch_related('class_categories')
        }
        self.built_snapshot = True

    def _build_furnishings_snapshot(self):
        """Index the non-classroom resources grouped with each classroom.

        Mirrors Resource.associated_resources(), which is what
        ClassSection.unsatisfied_requests() consults, but in two queries
        instead of several per section.
        """
        res_group_ids = {room.res_group_id
                         for rooms in self._classrooms.values()
                         for room in rooms
                         if room.res_group_id is not None}
        furnishing_types = defaultdict(set)
        if res_group_ids:
            grouped = Resource.objects.filter(res_group__in=res_group_ids) \
                                      .exclude(res_type__name='Classroom') \
                                      .values_list('res_group_id', 'res_type_id')
            for res_group_id, res_type_id in grouped:
                furnishing_types[res_group_id].add(res_type_id)
        #   Plain dict: a room with no group has nothing grouped with it, and
        #   reads shouldn't add keys to the snapshot.
        self._furnishing_types_by_group = dict(furnishing_types)

    def _unsatisfied_requests(self, section):
        """The snapshot equivalent of ClassSection.unsatisfied_requests()."""
        requests = self._requests[section.id]
        classrooms = self._classrooms[section.id]
        if not classrooms:
            return requests
        satisfied = self._furnishing_types_by_group.get(classrooms[0].res_group_id, frozenset())
        return [request for request in requests if request.res_type_id not in satisfied]

    def _all_class_sections(self, include_walkins=True):
        self._build_snapshot()
        return self.all_sections if include_walkins else self.all_nonwalkins

    def _section_meeting_times(self, section):
        return self._meeting_times[section.id]

    def _section_resources(self, section):
        return self._resources[section.id]

    def _section_classrooms(self, section):
        return self._classrooms[section.id]

    def _section_room_at(self, section, timeslot):
        return self._classroom_by_time[section.id].get(timeslot.id)

    def _section_teachers(self, section):
        return self._teachers[section.id]

    def _sections_by_teacher_index(self):
        self._build_snapshot()
        return self._sections_by_teacher

    def _sections_for_class(self, class_id):
        self._build_snapshot()
        return self._sections_by_class.get(class_id, [])

    def _section_moderators(self, section):
        return self._moderators[section.id]

    def _available_times(self, user):
        if user not in self._available_times_by_user:
            self._available_times_by_user[user] = set(
                user.getAvailableTimes(self.p, ignore_classes=True, ignore_moderation=True))
        return self._available_times_by_user[user]

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
            mt = self._section_meeting_times(s)
            rooms = self._section_classrooms(s)
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
            mt = self._section_meeting_times(s)
            rooms = self._section_classrooms(s)
            res_events = sorted([x.event for x in rooms])
            if res_events != mt:
                output.append({"Section": s, "Resource events": res_events,
                               "Meeting times": mt})
        return self.formatter.format_table(output,
            {"headings": ["Section", "Resource events", "Meeting times"]})

    def classes_which_cover_lunch(self):
        l = []
        for s in self._all_class_sections(include_walkins=False):
            mt = self._section_meeting_times(s)
            for lunch in self.lunch_blocks:
                if len(lunch) == 0:
                    pass
                elif all(b in mt for b in lunch):
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

    def unapproved_scheduled_classes(self):
        #   This check deliberately looks outside the main snapshot, which only
        #   holds approved sections; unapproved ones are the whole point here.
        sections = ClassSection.objects.filter(status__lt=10, parent_class__parent_program=self.p) \
                                       .select_related('parent_class') \
                                       .prefetch_related('meeting_times', 'resourceassignment_set')
        output = [sec for sec in sections
                  if sec.meeting_times.all() or sec.resourceassignment_set.all()]
        return self.formatter.format_list(output, ["Classes"])

    def teachers_teaching_two_classes_same_time(self):
        if self.p.hasModule("TeacherModeratorModule"):
            name_heading = 'Teacher/' + self.p.getModeratorTitle().capitalize() + "'s Name"
        else:
            name_heading = "Teacher's Name"
        d = self._timeslot_dict(slot=lambda: {})
        l = []
        for s in self._all_class_sections():
            mt = self._section_meeting_times(s)
            for t in mt:
                for teach in self._section_teachers(s):
                    if not teach in d[t]:
                        d[t][teach] = str(s) + (" (Teacher)" if self.p.hasModule("TeacherModeratorModule") else "")
                    else:
                        l.append({"Username": teach, name_heading: teach.name(), "Timeslot": t,
                                  "Section 1": str(s) + (" (Teacher)" if self.p.hasModule("TeacherModeratorModule") else ""), "Section 2": d[t][teach]})
                for mod in self._section_moderators(s):
                    if not mod in d[t]:
                        d[t][mod] = str(s) + " (" + str(self.p.getModeratorTitle().capitalize()) + ")"
                    else:
                        l.append({"Username": mod, name_heading: mod.name(), "Timeslot": t,
                                  "Section 1": str(s) + " (" + str(self.p.getModeratorTitle().capitalize()) + ")", "Section 2": d[t][mod]})
        return self.formatter.format_table(l, {'headings': ["Username", name_heading, "Timeslot", "Section 1", "Section 2"]})

    def multiple_classes_same_resource_same_time(self):
        d = self._timeslot_dict(slot=lambda: {})
        l = []
        for s in self._all_class_sections(include_walkins=False):
            mt = self._section_meeting_times(s)
            resources = self._section_resources(s)
            for t in mt:
                for r in resources:
                    if not r in d[t]:
                        d[t][r] = s
                    else:
                        l.append({"Timeslot": t, "Resource":r, "Section 1":s, "Section2":d[t][r]})
        return self.formatter.format_table(l, {"headings": ["Resource", "Timeslot", "Section 1", "Section 2"]})

    def room_capacity_mismatch(self, lower_reporting_ratio=0.5, upper_reporting_ratio=1.5):
        l = []
        for s in self._all_class_sections(include_walkins=False):
            r = self._section_classrooms(s)
            if len(r) > 0:
                room = r[0]
                cls = s.parent_class
                if room.num_students < lower_reporting_ratio*cls.class_size_max or room.num_students > upper_reporting_ratio*cls.class_size_max:
                    l.append({"Section": str(s), "Class Max": cls.class_size_max, "Room Max": room.num_students})
        return self.formatter.format_table(l, {'headings': ["Section", "Class Max", "Room Max"]})

    def hungry_teachers(self, ignore_open_classes=True):
        open_class_cat_id = self.p.open_class_category.id if ignore_open_classes else None

        #   One section per (timeslot, teacher); a teacher double-booked in a
        #   block is reported by teachers_teaching_two_classes_same_time.
        section_by_block = defaultdict(dict)
        for s in self._all_class_sections():
            for t in self._section_meeting_times(s):
                for teacher in self._section_teachers(s):
                    section_by_block[t].setdefault(teacher, s)

        bads = []
        for lunch in self.lunch_blocks:
            if not lunch:
                continue
            #   Teachers who are busy for every block of this day's lunch.
            teachers = set(section_by_block[lunch[0]])
            for block in lunch[1:]:
                teachers &= set(section_by_block[block])
            for t in sorted(teachers, key=lambda teacher: teacher.username):
                classes = [section_by_block[block][t] for block in lunch]
                if ignore_open_classes and open_class_cat_id in [c.category.id for c in classes]:
                    continue
                #converts the list of class section objects to a single string
                str1 = ', '
                classes = str1.join([str(c) for c in classes])
                bads.append({
                    'Username': t,
                    'Teacher Name': t.name(),
                    'Classes over lunch': classes,
                    })
        return self.formatter.format_table(bads,
                        {'headings': ['Username', 'Teacher Name', 'Classes over lunch']},
                        help_text="A list of teachers scheduled to teach " +
                        "during all lunch blocks of any day. Requires that " +
                        "lunch blocks are set up for the program. Ignores " +
                        "teachers who are teaching at least one " +
                        "open class / walk-in activity during that day's " +
                        "lunch.")

    #for classes_by_category and capacity_by_category
    def _calculate_d_categories(self):
        if len(self.d_categories) > 0:
            return self.d_categories

        self.class_categories =  list(self.p.class_categories.all().values_list('category', flat=True))

        #not regular class categories
        open_class_cat = self.p.open_class_category.category
        if open_class_cat in self.class_categories: self.class_categories.remove(open_class_cat)
        lunch_category = ClassCategories.get_lunch()
        if lunch_category is not None and lunch_category.category in self.class_categories:
            self.class_categories.remove(lunch_category.category)

        #generating a dictionary of class categories
        class_cat_d = {}
        for cat in self.class_categories:
            class_cat_d[cat] = 0
        def class_category_dict():
            return deepcopy(class_cat_d)

        #populating it with data
        d_classes = self._timeslot_dict(slot=class_category_dict)
        d_capacity = self._timeslot_dict(slot=class_category_dict)
        for s in self._all_class_sections():
            mt = self._section_meeting_times(s)
            for t in mt:
                #   Handle classes not in program's list of class categories
                #   (edge case in the event of manual modifications)
                sc = s.category.category
                if sc not in d_classes[t]:
                    d_classes[t][sc] = 0
                if sc not in d_capacity[t]:
                    d_capacity[t][sc] = 0
                d_classes[t][sc] += 1
                d_capacity[t][sc] += s.capacity

        self.d_categories = {"classes":d_classes, "capacity":d_capacity}
        return self.d_categories

    def capacity_by_category(self):
        self._calculate_d_categories()
        return  self.formatter.format_table(self.d_categories["capacity"], {"headings": self.class_categories})


    def classes_by_category(self):
        self._calculate_d_categories()
        return  self.formatter.format_table(self.d_categories["classes"], {"headings": self.class_categories})


    def _calculate_d_grades(self):
        if len(self.d_grades) > 0:
            return self.d_grades

        self.grades = self.p.classregmoduleinfo.getClassGrades()
        grades_d = {}
        for grade in self.grades:
            grades_d[grade] = 0
        def grade_dict():
            return deepcopy(grades_d)

        #populating it with data
        d_classes = self._timeslot_dict(slot=grade_dict)
        d_capacity = self._timeslot_dict(slot=grade_dict)
        for s in self._all_class_sections(include_walkins=False):
            cls = s.parent_class
            mt = self._section_meeting_times(s)
            for t in mt:
                for grade in range(cls.grade_min, cls.grade_max + 1, 1):
                    d_classes[t][grade] += 1
                    d_capacity[t][grade] += s.capacity
        self.d_grades = { "capacity": d_capacity, "classes": d_classes }
        return self.d_grades

    def capacity_by_grade(self):
        self._calculate_d_grades()
        return  self.formatter.format_table(self.d_grades["capacity"], {"headings": self.grades})

    def classes_by_grade(self):
        self._calculate_d_grades()
        return  self.formatter.format_table(self.d_grades["classes"], {"headings": self.grades})

    def admins_teaching_per_timeblock(self):
        key_string = "Admin Usernames"
        name_string = "Admin Names"
        num_string = "Number"
        def admin_dict():
            return { key_string: [], name_string: [] }

        d = self._timeslot_dict(slot=admin_dict)
        for s in self._all_class_sections():
            teachers = self._section_teachers(s)
            admin_teachers = [t for t in teachers if t.isAdministrator()]
            for a in admin_teachers:
                mt = self._section_meeting_times(s)
                for t in mt:
                    d[t][name_string].append(a.name())
                    d[t][key_string].append(str(a))
        for k in d:
            d[k][num_string] = len(d[k][key_string])
        for l in d:
            str1 = ", "
            d[l][key_string] = str1.join(d[l][key_string])
            d[l][name_string] = str1.join(d[l][name_string])
        return self.formatter.format_table(d,
            {"headings": [num_string, key_string, name_string]})

    def _calculate_classes_missing_resources(self):
        if self.calculated_classes_missing_resources:
            return
        l_resources = []
        l_classrooms = []
        l_mod = []
        for s in self._all_class_sections():
            meeting_times = self._section_meeting_times(s)
            first_hour = meeting_times[0] if meeting_times else None
            classrooms = self._section_classrooms(s)
            classroom = classrooms[0] if classrooms else None
            unsatisfied_requests = self._unsatisfied_requests(s)
            if len(unsatisfied_requests) > 0:
                for u in unsatisfied_requests:
                    #I'm not sure how MIT specific is.  I don't have access to other databases to know whether this will work
                    #on other ESPs' websites
                    if str.lower(str(u.res_type.name)) == "classroom space":
                        if not u.desired_value == "No preference":
                            l_classrooms.append({ "Section": s, "First Hour": first_hour, "Requested Type": u.desired_value, "Classroom": classroom })
                    else:
                        l_resources.append({ "Section": s, "First Hour": first_hour, "Unfulfilled Request": u, "Classroom": classroom })
            for moderator in self._section_moderators(s):
                #   None means the moderator has no ModeratorRecord at all.
                categories = self._moderator_categories.get(moderator.id)
                if categories is None or s.parent_class.category not in categories:
                    mod_recs_list = ", ".join(cat.category for cat in categories or []) or "No selection"
                    l_mod.append({ "Section": s, "Section Time": first_hour, "Requested Category": mod_recs_list, self.p.getModeratorTitle(): moderator })
        self.l_wrong_classroom_type = l_classrooms
        self.l_missing_resources = l_resources
        self.l_mod_missing = l_mod
        self.calculated_classes_missing_resources = True
        return [l_classrooms, l_resources]

    def classes_missing_resources(self):
        self._calculate_classes_missing_resources()
        return self.formatter.format_table(self.l_missing_resources, {"headings":["Section", "Unfulfilled Request", "Classroom", "First Hour"]})

    def missing_resources_by_hour(self):
        self._calculate_classes_missing_resources()
        key_string = "Unfulfilled Request Numbers"
        num_string = "num"
        def ts_dict():
            return { }

        timeslots = self._timeslot_dict(slot=ts_dict)
        for sec in self.l_missing_resources:
            sec_times = self._section_meeting_times(sec["Section"])
            for time in sec_times:
                timeslots[time][sec["Unfulfilled Request"].res_type] = \
                    timeslots[time].get(sec["Unfulfilled Request"].res_type, 0) + 1
        final_data = []
        for t in timeslots:
            for r in timeslots[t]:
                final_data.append({"Timeblock": t, "Resource type": r,
                               "Number": timeslots[t][r]})
        final_data.sort(key=lambda d: d["Timeblock"].start)
        return self.formatter.format_table(
              final_data,
              {"headings": ["Timeblock", "Resource type", "Number"]})

    def wrong_classroom_type(self):
        self._calculate_classes_missing_resources()
        return self.formatter.format_table(self.l_wrong_classroom_type, {"headings": ["Section", "Requested Type", "Classroom", "First Hour"]})

    def teachers_unavailable(self):
        l = []
        for s in self._all_class_sections():
            for t in self._section_teachers(s):
                available = self._available_times(t)
                for e in self._section_meeting_times(s):
                    if e not in available:
                        l.append({"Teacher": t, "Time": e, "Section": s})
        return self.formatter.format_table(l, {"headings": ["Section", "Teacher", "Time"]})

    def teachers_who_like_running(self):
        l = []
        sections_by_teacher = self._sections_by_teacher_index()
        for teacher in sorted(sections_by_teacher, key=lambda user: user.username):
            #   Sections without meeting times can't be run between.
            sections = sorted((s for s in sections_by_teacher[teacher]
                               if self._section_meeting_times(s)),
                              key=lambda s: (self._section_meeting_times(s)[0].start, s.id))
            for first, second in zip(sections, sections[1:]):
                time0 = max(self._section_meeting_times(first), key=lambda event: event.end)
                time1 = self._section_meeting_times(second)[0]
                #   Compare the room they finish in with the room they start in.
                room0 = self._section_room_at(first, time0)
                room1 = self._section_room_at(second, time1)
                if room0 is None or room1 is None:
                    continue
                if (time1.start-time0.end).total_seconds() < 1200 and room0.name != room1.name:
                    l.append({"Username": teacher, "Teacher Name": teacher.name(), "Section 1": first, "Section 2": second, "Room 1": room0, "Room 2": room1})
        return self.formatter.format_table(l,
                        {"headings": ["Username", "Teacher Name", "Section 1", "Section 2",
                                      "Room 1", "Room 2"]},
                        help_text="A list of teachers teaching two " +
                        "back-to-back classes (defined as two classes " +
                        "within 20 minutes of each other) in two different " +
                        "locations.")


    def no_overlap_classes(self):
        '''Gets a list of classes from the tag no_overlap_classes, and checks that they don't overlap.  The tag should contain a dict of {'comment': [list,of,class,ids]}.'''
        classes = json.loads(Tag.getProgramTag('no_overlap_classes',program=self.p))
        bad_classes = []
        for key, class_ids in classes.items():
            #   Keyed by timeblock description; a class with several sections in
            #   one block only counts once, since it can't overlap itself.
            overlaps = defaultdict(set)
            for class_id in class_ids:
                for section in self._sections_for_class(class_id):
                    for meeting_time in self._section_meeting_times(section):
                        overlaps[meeting_time.description].add(section.parent_class)
            for event, overlapping in overlaps.items():
                if len(overlapping)>1:
                    bad_classes.append({
                        'Comment': key,
                        'Timeblock': event,
                        'Classes': sorted(overlapping, key=lambda cls: cls.id)
                        })
        return self.formatter.format_table(bad_classes,
                {'headings': ['Comment', 'Timeblock', 'Classes']},
                help_text="Given a list of classes that should not overlap, compute which overlap.  This is to be used for example for classes using the same materials which are not tracked by the website, or to check that directors' classes don't overlap.  The classes should be put in the Tag no_overlap_classes, in the format of a dictionary with keys various comments (e.g. 'classes using the Quiz Bowl buzzers') and values as corresponding lists of class IDs."
                )

    def special_classroom_types(self):
        """
        Check special classrooms types (music, computer, kitchen).
        Configuration Tag: special_classroom_types, a dictionary mapping
        resource request type desired_value regexes to a list of classrooms (by
        resource ID). Any classroom whose name matches the regex will
        automatically be included.
        """
        DEFAULT_CONFIG = {r'^.*(computer|cluster).*$': [],
                          r'^.*music.*$': [],
                          r'^.*kitchen.*$': []}
        config = json.loads(Tag.getProgramTag('special_classroom_types',
                                              program=self.p))
        config = config if config else DEFAULT_CONFIG

        HEADINGS = ["Class Section", "Unfulfilled Request", "Current Room"]
        mismatches = []

        for type_regex, matching_rooms in DEFAULT_CONFIG.items():
            resource_requests = ResourceRequest.objects.filter(
                res_type__program=self.p, desired_value__iregex=type_regex)

            for rr in resource_requests:
                #   Read the rooms once: querying twice can see a reschedule
                #   land in between and index into an empty result.
                rooms = list(rr.target.classrooms()) if rr.target_id else []
                if all(room.id in matching_rooms or
                       re.match(type_regex, room.name, re.IGNORECASE)
                       for room in rooms):
                    continue

                mismatches.append({
                        HEADINGS[0]: rr.target,
                        HEADINGS[1]: rr.desired_value,
                        HEADINGS[2]: rooms[0].name
                        })

        return self.formatter.format_table(mismatches,
                                           {'headings': HEADINGS},
                                           help_text=self.special_classroom_types.__doc__)

    # This isn't really a scheduling check. It's a check that's useful
    # to run before scheduling. But it works well with the format and
    # this way everyone else doesn't have to rediscover the round_to
    # argument to ESPUser.getTaughtTime() every year.
    def inflexible_teachers(self):
        """
        Teachers who have registered almost as many hours of classes
        as hours of availability. Intended to be run before scheduling,
        and will not change as classes are scheduled.
        """
        teachers = self.p.teachers()['class_submitted']
        inflexible = []
        for teacher in teachers:
            # This will break if we ever start having class blocks
            # that aren't an hour long
            availability = len(teacher.getAvailableTimes(self.p, ignore_classes=True))
            class_hours = teacher.getTaughtTime(program=self.p, round_to=1).seconds/3600
            delta = availability - class_hours
            # Arbitrary formula, seems to do a good job of catching the cases I care about
            if (availability == 0) or (class_hours/float(availability) >= 2/float(3)):
                inflexible.append({'Username': teacher.username,
                              'Teacher Name': teacher.name(),
                              'Class hours': class_hours,
                              'Available hours': availability,
                              'Free hours': delta})
        return self.formatter.format_table(inflexible,
                                           {'headings': ['Username', 'Teacher Name', 'Class hours',
                                                         'Available hours',
                                                         'Free hours']},
                                           help_text=self.inflexible_teachers.__doc__)

    def mismatched_moderators(self):
        """
        Moderators who have indicated a preference for which class type they would like to moderate and are moderating another type of class.
        """
        self._calculate_classes_missing_resources()
        return self.formatter.format_table(self.l_mod_missing, {"headings": ["Section", "Section Time", "Requested Category", self.p.getModeratorTitle()]})

    def unavailable_moderators(self):
        """
        Moderators who are moderating at a time at which they are not available.
        """
        l = []
        for s in self._all_class_sections():
            for m in self._section_moderators(s):
                available = self._available_times(m)
                for e in self._section_meeting_times(s):
                    if e not in available:
                        l.append({self.p.getModeratorTitle(): m, "Time": e, "Section": s})
        return self.formatter.format_table(l, {"headings": ["Section", self.p.getModeratorTitle(), "Time"]})

    def _consecutive_timeslot_pairs(self):
        pairs = []
        timeslots = sorted(self.p.getTimeSlotList(), key=lambda ts: ts.start)

        contiguous_tolerance = int(Tag.getProgramTag('timeblock_contiguous_tolerance', program=self.p) or 0)
        for contiguous_group in Event.group_contiguous(timeslots, contiguous_tolerance):
            contiguous_group = sorted(contiguous_group, key=lambda ts: ts.start)
            for i in range(len(contiguous_group) - 1):
                current_slot = contiguous_group[i]
                next_slot = contiguous_group[i + 1]
                if current_slot.start.date() == next_slot.start.date():
                    pairs.append((current_slot, next_slot))
        return pairs

    def _moderator_room_assignments(self):
        """Build moderator->room and room->moderators maps for each timeslot."""
        by_moderator = defaultdict(dict)
        by_room = defaultdict(lambda: defaultdict(set))

        for section in self._all_class_sections():
            meeting_times = set(self._section_meeting_times(section))
            if not meeting_times:
                continue

            room_by_timeslot = {}
            for room in self._section_classrooms(section):
                if room.event in meeting_times:
                    room_by_timeslot[room.event] = room.name

            for timeslot, room_name in room_by_timeslot.items():
                for moderator in self._section_moderators(section):
                    by_moderator[timeslot][moderator] = room_name
                    by_room[timeslot][room_name].add(moderator)

        return by_moderator, by_room

    def _dependency_severity(self, chain_length, has_loop):
        if has_loop:
            return 'High'
        if chain_length >= 5:
            return 'High'
        if chain_length >= 3:
            return 'Medium'
        return 'Low'

    def _trace_dependency_chains(self, start_moderator, first_dependency, dependency_graph):
        """Trace all dependency branches from one starting dependency edge."""
        stack = [(start_moderator, [start_moderator, first_dependency])]
        chains = []

        while stack:
            _, chain = stack.pop()
            current = chain[-1]
            next_candidates = sorted(
                dependency_graph.get(current, set()),
                key=lambda user: user.username,
            )

            if not next_candidates:
                chains.append((chain, False))
                continue

            for candidate in next_candidates:
                if candidate == start_moderator:
                    chains.append((chain + [start_moderator], True))
                elif candidate not in chain:
                    stack.append((start_moderator, chain + [candidate]))
                else:
                    # Internal cycle not returning to the start moderator.
                    chains.append((chain + [candidate], False))

        # Deduplicate equivalent chain signatures.
        deduped = []
        seen = set()
        for chain, has_loop in chains:
            signature = (tuple(user.username for user in chain), has_loop)
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append((chain, has_loop))
        return deduped

    def moderator_movement_dependency_loops(self):
        """
        Moderators with room-switch dependencies across consecutive blocks.
        A loop indicates a chain that returns to the starting moderator.
        """
        moderator_rooms, room_moderators = self._moderator_room_assignments()
        output_rows = []

        for current_slot, next_slot in self._consecutive_timeslot_pairs():
            dependency_graph = defaultdict(set)
            current_assignments = moderator_rooms.get(current_slot, {})
            next_assignments = moderator_rooms.get(next_slot, {})

            for moderator, current_room in current_assignments.items():
                next_room = next_assignments.get(moderator)
                if next_room is None or next_room == current_room:
                    continue

                replacements = room_moderators.get(next_slot, {}).get(current_room, set())
                for replacement in replacements:
                    if replacement == moderator:
                        continue
                    replacement_current_room = current_assignments.get(replacement)
                    if replacement_current_room is None or replacement_current_room == current_room:
                        continue
                    dependency_graph[moderator].add(replacement)

            for moderator in sorted(dependency_graph.keys(), key=lambda user: user.username):
                for first_dependency in sorted(dependency_graph[moderator], key=lambda user: user.username):
                    chains = self._trace_dependency_chains(moderator, first_dependency, dependency_graph)
                    for chain, has_loop in chains:
                        dependency_count = max(len(chain) - 1, 0)
                        chain_str = ' -> '.join(user.username for user in chain)
                        output_rows.append({
                            "Current Block": current_slot,
                            "Next Block": next_slot,
                            self.p.getModeratorTitle().capitalize(): moderator,
                            "Dependency Chain": chain_str,
                            "Dependency Count": dependency_count,
                            "Severity": self._dependency_severity(dependency_count, has_loop),
                            "Loop": "Yes" if has_loop else "No",
                        })

        return self.formatter.format_table(
            output_rows,
            {
                "headings": [
                    "Current Block",
                    "Next Block",
                    self.p.getModeratorTitle().capitalize(),
                    "Dependency Chain",
                    "Dependency Count",
                    "Severity",
                    "Loop",
                ]
            },
            help_text=(
                "Tracks moderator room switches across consecutive blocks and reports "
                "movement dependency chains. Rows marked Loop=Yes are hard loops that "
                "return to the same moderator and typically require manual intervention."
            ),
        )

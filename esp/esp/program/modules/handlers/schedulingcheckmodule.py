from django.http import HttpResponse
from esp.program.models import Program, ClassSection, ClassSubject
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


class SchedulingCheckModule(ProgramModuleObj):

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
              context = {'check_list': s.all_diagnostics, 'unreviewed': "unreviewed" in request.GET}
              return render_to_response(self.baseDir()+'output.html', request, context)

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
        output["headings"] = map(str, heading) # no headings

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
        output["headings"] = map(str, headings)
        output["body"] = [self._table_row([row[h] for h in headings]) for row in d]
        return output

    def _format_dict_table(self, d, headings, help_text=""): #needs verify
        headings = [""] + headings[:]
        output = {}
        output["help_text"] = help_text
        output["headings"] = map(str, headings)
        output["body"] = [self._table_row([key] + [row[h] for h in headings if h]) for key, row in sorted(d.iteritems())]
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
               diagnostics = self.all_diagnostics
          return [getattr(self, diag)() for diag in diagnostics]


     # Update this to add a scheduling check.
     all_diagnostics = [
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
         ('teachers_teaching_two_classes_same_time', 'Teachers teaching two classes at once'),
         ('teachers_who_like_running', 'Teachers who like running'),
         ('hungry_teachers', 'Hungry teachers'),
         ('inflexible_teachers', 'Teachers with limited flexibility'),
         #Information Diagnostics
         ('classes_by_category', 'Number of classes in each block by category'),
         ('capacity_by_category', 'Total capacity in each block by category'),
         ('classes_by_grade', 'Number of classes in each block by grade'),
         ('capacity_by_grade', 'Total capacity in each block by grade'),
         ('admins_teaching_per_timeblock', 'Admins teaching per timeslot')

     ]

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
               qs = qs.prefetch_related('meeting_times', 'resourceassignment_set', 'resourceassignment_set__resource', 'parent_class__teachers')
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
            rooms = s.getResources()
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
            rooms = s.getResources()
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

     def unapproved_scheduled_classes(self):
         output = []
         sections = ClassSection.objects.filter(status__lt=10, parent_class__parent_program=self.p)
         for sec in sections:
             if sec.get_meeting_times() or sec.getResources():
                 output.append(sec)
         return self.formatter.format_list(output, ["Classes"])

     def teachers_teaching_two_classes_same_time(self):
          d = self._timeslot_dict(slot=lambda: {})
          l = []
          for s in self._all_class_sections():
               mt =  s.get_meeting_times()
               for t in mt:
                    for teach in s.teachers:
                         if not teach in d[t]:
                              d[t][teach] = s
                         else:
                              l.append({"Username": teach, "Teacher Name": teach.name(), "Timeslot":t, "Section 1": s, "Section 2": d[t][teach]})
          return self.formatter.format_table(l, {'headings': ["Username", "Teacher Name", "Timeslot", "Section 1", "Section 2"]})

     def multiple_classes_same_resource_same_time(self):
          d = self._timeslot_dict(slot=lambda: {})
          l = []
          for s in self._all_class_sections(include_walkins=False):
               mt =  s.get_meeting_times()
               resources = s.getResources()
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
               r = s.classrooms()
               if len(r) > 0:
                    room = r[0]
                    cls = s.parent_class
                    if room.num_students < lower_reporting_ratio*cls.class_size_max or room.num_students > upper_reporting_ratio*cls.class_size_max:
                         l.append({"Section": str(s), "Class Max": cls.class_size_max, "Room Max": room.num_students})
          return self.formatter.format_table(l, {'headings': ["Section", "Class Max", "Room Max"]})

     def hungry_teachers(self, ignore_open_classes=True):
         lunches = self.lunch_blocks
         if ignore_open_classes:
             open_class_cat = self.p.open_class_category
         bads = []
         for lunch in lunches:
             if lunch:
                 q=ESPUser.objects.all()
                 for block in lunch:
                     q=q.filter(classsubject__sections__meeting_times=block)
                 for t in q.distinct():
                     classes = [ClassSection.objects.filter(parent_class__teachers=t,meeting_times=block)[0] for block in lunch]
                     if open_class_cat.id not in [c.category.id for c in classes]:
                         #converts the list of class section objects to a single string
                         str1 = ', '
                         classes = str1.join([unicode(c) for c in classes])
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
          lunch_cat = "Lunch"
          if lunch_cat in self.class_categories: self.class_categories.remove(lunch_cat)

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
               mt =  s.get_meeting_times()
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
               mt =  s.get_meeting_times()
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
               teachers = s.parent_class.get_teachers()
               admin_teachers = [t for t in teachers if t.isAdministrator()]
               for a in admin_teachers:
                    mt =  s.get_meeting_times()
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
         for s in self._all_class_sections():
             meeting_times = s.get_meeting_times()
             first_hour = meeting_times[0] if meeting_times else None
             classrooms = s.classrooms()
             classroom = classrooms[0] if classrooms else None
             unsatisfied_requests = s.unsatisfied_requests()
             if len(unsatisfied_requests) > 0:
                 for u in unsatisfied_requests:
                     #I'm not sure how MIT specific is.  I don't have access to other databases to know whether this will work
                     #on other ESPs' websites
                     if str.lower(str(u.res_type.name)) == "classroom space":
                         if not u.desired_value == "No preference":
                             l_classrooms.append({ "Section": s, "First Hour": first_hour, "Requested Type": u.desired_value, "Classroom": classroom })
                     else:
                         l_resources.append({ "Section": s, "First Hour": first_hour, "Unfulfilled Request": u, "Classroom": classroom })
         self.l_wrong_classroom_type = l_classrooms
         self.l_missing_resources = l_resources
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
             sec_times = sec["Section"].get_meeting_times()
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
             for t in s.teachers:
                 available = t.getAvailableTimes(s.parent_program, ignore_classes=True)
                 for e in s.get_meeting_times():
                     if e not in available:
                         l.append({"Teacher": t, "Time": e, "Section": s})
         return self.formatter.format_table(l, {"headings": ["Section", "Teacher", "Time"]})

     def teachers_who_like_running(self):
         l = []
         teachers = self.p.teachers()['class_approved'].distinct()
         for teacher in teachers:
             if self.incl_unreview:
                 sections = ClassSection.objects.filter(
                     parent_class__in=teacher.getTaughtClassesFromProgram(self.p).filter(status__gte=0).distinct(),status__gte=0).distinct().order_by('meeting_times__start')
             else:
                 sections = ClassSection.objects.filter(
                     parent_class__in=teacher.getTaughtClassesFromProgram(self.p).filter(status__gt=0).distinct(),status__gt=0).distinct().order_by('meeting_times__start')
             for i in range(sections.count()-1):
                 try:
                     time1 = sections[i+1].meeting_times.all().order_by('start')[0]
                     time0 = sections[i].meeting_times.all().order_by('-end')[0]
                     room0 = sections[i].initial_rooms()[0]
                     room1 = sections[i+1].initial_rooms()[0]
                     if (time1.start-time0.end).total_seconds() < 1200 and sections[i].initial_rooms().count() + sections[i+1].initial_rooms().count() and room0.name != room1.name:
                         l.append({"Username": teacher, "Teacher Name": teacher.name(), "Section 1": sections[i], "Section 2": sections[i+1], "Room 1": room0, "Room 2": room1})
                 except BaseException:
                     continue
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
         classes_lookup = {x.id: x for x in ClassSubject.objects.filter(id__in=sum(classes.values(),[]))}
         bad_classes = []
         for key, l in classes.iteritems():
             eventtuples = list(Event.objects.filter(meeting_times__parent_class__in=l).values_list('description', 'meeting_times', 'meeting_times__parent_class'))
             overlaps = {}
             for event, sec, cls in eventtuples:
                 if event in overlaps:
                     overlaps[event].append(classes_lookup[cls])
                 else:
                     overlaps[event]=[classes_lookup[cls]]
             for event in overlaps:
                 if len(overlaps[event])>1:
                     bad_classes.append({
                         'Comment': key,
                         'Timeblock': event,
                         'Classes': overlaps[event]
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

         for type_regex, matching_rooms in DEFAULT_CONFIG.iteritems():
             resource_requests = ResourceRequest.objects.filter(
                 res_type__program=self.p, desired_value__iregex=type_regex)

             for rr in resource_requests:
                 if all(room.id in matching_rooms or
                        re.match(type_regex, room.name, re.IGNORECASE)
                        for room in rr.target.classrooms()):
                     continue

                 mismatches.append({
                         HEADINGS[0]: rr.target,
                         HEADINGS[1]: rr.desired_value,
                         HEADINGS[2]: rr.target.classrooms()[0].name
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
             if class_hours/float(availability) >= 2/float(3):
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

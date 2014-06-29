from esp.program.models import Program, ClassSection, ClassSubject
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from copy import deepcopy
from math import ceil
from esp.cal.models import *
from datetime import date
from esp.web.util.main import render_to_response
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
import json

class SchedulingCheckModule(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Scheduling Diagnostics",
            "link_title": "Run Scheduling Diagnostics",
            "module_type": "manage",
            "seq": 10
            }

    @main_call
    @needs_admin
    def scheduling_checks(self, request, tl, one, two, module, extra, prog):
         s = SchedulingCheckRunner(prog)
         results = s.run_diagnostics()
         context = {'checks': results}
         return render_to_response(self.baseDir()+'output.html', request, context)

    class Meta:
        proxy = True

#For formatting output.  The default is to use HTMLSCFormatter, but someone writing a script
#may want to use RawSCFormatter to get the original data structures
class RawSCFormatter:
    def format_table(self, l, title, options={}, help_text=""):
        return l

    def format_list(self, l, title, options={}, help_text=""):
        return l

class HTMLSCFormatter:
    #requires: d, a two level dictionary where the the first set of
    #   keys are the headings expected on the side of the table, and
    #   the second set are the headings expected on the top of the table
    def format_table(self, d, title, options={}, help_text=""):
        if type(d) == list:
            return self._format_list_table(d, title, options['headings'], help_text=help_text)
        else:
            return self._format_dict_table(d, title, options['headings'], help_text=help_text)

    def format_list(self, l, title, help_text=""):
        output = self._table_title(title, [title], help_text=help_text)
        for row in l:
            output += self._table_row([row])
        output += "</table>"
        return output

    def _table_start(self):
        output = "<table cellpadding=10 style=\"border: 1px solid black; border-collapse: collapse;\">"
        return output

    def _table_title(self, title, headings, help_text=""):
        output = self._table_start()
        output += "<tr><th colspan=\""+str(len(headings))+"\" align=\"center\">" + str(title) + "</th></tr>"
        if help_text:
            output += "<tr><td colspan=\""+str(len(headings))+"\" align=\"center\">" + str(help_text) + "</td></tr>"
        return output

    def _table_headings(self, headings):
        #column headings
        next_row = ""
        for h in headings:
            next_row = next_row + "<th><div style=\"cursor: pointer;\">" + str(h) + "</div></th>"
        next_row = next_row + "</tr></thread>"
        return next_row

    def _table_row(self, row):
        next_row = ""
        for r in row:
            #displaying lists is sometimes borked.  This makes it not borked
            if type(r) == list:
                r = [str(i) for i in r]
            next_row += "<td>" + str(r) + "</td>"
        next_row += "</tr>"
        return next_row
        
    def _format_list_table(self, d, title, headings, help_text=""):
        output = self._table_title(title, headings, help_text=help_text)
        output = output + self._table_headings(headings)
        for row in d:
            ordered_row = [row[h] for h in headings]
            output = output + self._table_row(ordered_row) 
        output = output + "</table>"
        return output

    def _format_dict_table(self, d, title, headings, help_text=""):
        headings = [""] + headings[:]
        output = self._table_title(title, headings, help_text=help_text)
        output = output + self._table_headings(headings)

        for key, row in sorted(d.iteritems()):
            ordered_row = [row[h] for h in headings if h]
            output = output + self._table_row([key] + ordered_row)
        output += "</table>"
        return output

class SchedulingCheckRunner:
#Generate html report and generate text report functions?lingCheckRunner:
     def __init__(self, program, formatter=HTMLSCFormatter()):
          """
          high_school_only and lunch should be lists of indeces of timeslots for the high school
          only block and for lunch respectively
          """
          self.p = program
          self.formatter = formatter

          self.high_school_blocks = self._get_high_school_only()
          self.lunch_blocks = self._getLunchByDay()

          #things that we'll calculate lazilly
          self.listed_sections = False
          self.calculated_classes_missing_resources = False
          self.d_categories = []
          self.d_grades = []

     def _getLunchByDay(self):
        import numpy
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

     def _get_high_school_only(self):
          """  Returns a list of blocks which start after 7 PM.  At MIT, these blocks are high school
          only.  So this is a pretty MIT-Centric function.
          """
          l = []
          for ts in self.p.getTimeSlots():
               if ts.start.hour >= 19:
                    l.append(ts)
          return l

     def run_diagnostics(self):
         return [
             self.lunch_blocks_setup(),
             self.high_school_only_setup(),
             self.incompletely_scheduled_classes(),
             self.wrong_classroom_type(),
             self.classes_missing_resources(),
             self.multiple_classes_same_room_same_time(),
             self.teachers_unavailable(),
             self.teachers_teaching_two_classes_same_time(),
             self.classes_which_cover_lunch(),
             self.room_capacity_mismatch(),
             self.middle_school_evening_classes(),
             self.classes_by_category(),
             self.capacity_by_category(),
             self.classes_by_grade(),
             self.capacity_by_grade(),
             self.admins_teaching_per_timeblock(),
             self.teachers_who_like_running(),
             self.hungry_teachers(),
             self.no_overlap_classes(),
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

     #memoize the list of class sections in this program
     def _all_class_sections(self):
          if self.listed_sections:
               return self.all_sections
          else:
               qs = self.p.sections()
               #filter out walkins
               qs = qs.exclude(parent_class__category__id=self.p.open_class_category.id)
               #filter out non-approved classes
               qs = qs.exclude(status__lte=0)
               qs = qs.exclude(resourceassignment__isnull=True)
               #filter out lunch
               qs = qs.exclude(parent_class__category__category=u'Lunch')
               qs = qs.select_related('parent_class', 'parent_class__parent_program', 'parent_class__category')
               qs = qs.prefetch_related('meeting_times', 'resourceassignment_set', 'resourceassignment_set__resource', 'parent_class__teachers')
               self.all_sections = list(qs)
               self.listed_sections = True
               return self.all_sections


     #################################################
     #
     #    Diagnostic functions
     #
     #################################################
     def lunch_blocks_setup(self):
         lunch_block_strings = [[str(l) for l in lunch_block_list] for lunch_block_list in self.lunch_blocks]
         return self.formatter.format_list(lunch_block_strings, "Lunch Blocks")

     def high_school_only_setup(self):
         return self.formatter.format_list(self.high_school_blocks, "High School Only Blocks")

     def incompletely_scheduled_classes(self):
          problem_classes = []
          for s in self._all_class_sections():
               mt =  s.get_meeting_times()
               rooms = s.getResources()
               if(len(rooms) != ceil(s.duration)):
                    problem_classes.append(s)
               elif(len(rooms) != len(mt)):
                    problem_classes.append(s)
          return self.formatter.format_list(problem_classes, "Classes not completely scheduled:")

     def classes_which_cover_lunch(self):
          l = []
          for s in self._all_class_sections():
               mt =  s.get_meeting_times()
               for lunch in self.lunch_blocks:
                    if len(lunch) == 0:
                        pass
                    elif not (False in [b in mt for b in lunch]):
                         l.append(s)
          return self.formatter.format_list(l, "Classes which are scheduled over lunch")

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
                              l.append({"Teacher": teach, "Timeslot":t, "Section 1": s, "Section 2": d[t][teach]})
          return self.formatter.format_table(l, "Teachers teaching two classes at once", {'headings': ["Teacher", "Timeslot", "Section 1", "Section 2"]})

     def multiple_classes_same_room_same_time(self):
          d = self._timeslot_dict(slot=lambda: {})
          l = []
          for s in self._all_class_sections():
               mt =  s.get_meeting_times()
               rooms = s.classrooms()
               for t in mt:
                    for r in rooms:
                         if not r in d[t]:
                              d[t][r] = s
                         else:
                              l.append({"Timeslot": t, "Room":r, "Section 1":s, "Section2":d[t][r]})
          return self.formatter.format_table(l, "Double-booked rooms", {"headings": ["Room", "Timeslot", "Section 1", "Section 2"]})

     def middle_school_evening_classes(self):
          hso = set(self.high_school_blocks)
          sections = self._all_class_sections()
          #only middle school allowing classes
          sections = filter(lambda x: x.parent_class.grade_min < 9, sections)          
          #only classes in evening timeblocks
          sections = filter(lambda x: len(set(x.get_meeting_times()) & hso) > 0, sections )

          #reporting    
          self.formatter.format_list(sections, "Classes allowing middle school students during the high school only block")
          middle_school_only = filter(lambda x: x.parent_class.grade_max < 9, sections)
          return self.formatter.format_list(middle_school_only, "Classe with only middle school students during the high school only block")

     def room_capacity_mismatch(self, lower_reporting_ratio=0.5, upper_reporting_ratio=1.5):
          l = []
          for s in self._all_class_sections():
               r = s.classrooms()
               if len(r) > 0:
                    room = r[0]
                    cls = s.parent_class
                    if room.num_students < lower_reporting_ratio*cls.class_size_max or room.num_students > upper_reporting_ratio*cls.class_size_max:
                         l.append({"Section": str(s), "Class Max": cls.class_size_max, "Room Max": room.num_students})
          return self.formatter.format_table(l, "Class max size/room max size mismatches", {'headings': ["Section", "Class Max", "Room Max"]})

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
                     classes = [ClassSection.objects.get(parent_class__teachers=t,meeting_times=block) for block in lunch]
                     if open_class_cat.id not in [c.category.id for c in classes]:
                         bads.append({
                             'Teacher': t,
                             'Classes over lunch': classes,
                             })
         return self.formatter.format_table(bads,"Hungry Teachers",
                         {'headings': ['Teacher','Classes over lunch']},
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
         return  self.formatter.format_table(self.d_categories["capacity"], "Total capacity in each block by category.", {"headings": self.class_categories})
        

     def classes_by_category(self):
         self._calculate_d_categories()
         return  self.formatter.format_table(self.d_categories["classes"], "Number of classes in each block by category.", {"headings": self.class_categories})

         
     def _calculate_d_grades(self):
          if len(self.d_grades) > 0:
             return self.d_grades

          self.grades = self.p.getModuleExtension('ClassRegModuleInfo').getClassGrades()
          grades_d = {}
          for grade in self.grades:
               grades_d[grade] = 0
          def grade_dict():
               return deepcopy(grades_d)

          #populating it with data
          d_classes = self._timeslot_dict(slot=grade_dict)
          d_capacity = self._timeslot_dict(slot=grade_dict)
          for s in self._all_class_sections():
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
         return  self.formatter.format_table(self.d_grades["capacity"], "Total capacity in each block by grade.", {"headings": self.grades})
        

     def classes_by_grade(self):
         self._calculate_d_grades()
         return  self.formatter.format_table(self.d_grades["classes"], "Number of classes in each block by grade.", {"headings": self.grades})

     def admins_teaching_per_timeblock(self):
          key_string = "Admins Teaching"
          def admin_dict():
               return { key_string: [] }

          d = self._timeslot_dict(slot=admin_dict)
          for s in self._all_class_sections():
               teachers = s.parent_class.get_teachers()
               admin_teachers = [t for t in teachers if t.isAdministrator()]
               for a in admin_teachers:
                    mt =  s.get_meeting_times()
                    for t in mt:
                         d[t][key_string].append(str(a))
          return self.formatter.format_table(d, "Admins teaching per timeslot", {"headings":[key_string]})

     def _calculate_classes_missing_resources(self):
         if self.calculated_classes_missing_resources:
             return
         l_resources = []
         l_classrooms = []
         for s in self._all_class_sections():
             unsatisfied_requests = s.unsatisfied_requests()
             if len(unsatisfied_requests) > 0:
                 for u in unsatisfied_requests:
                     #I'm not sure how MIT specific is.  I don't have access to other databases to know whether this will work 
                     #on other ESPs' websites
                     if str.lower(str(u.res_type.name)) == "classroom space":
                         if not u.desired_value == "No preference":
                             l_classrooms.append({ "Section": s, "Requested Type": u.desired_value, "Classroom": s.classrooms()[0] })
                     else:
                         l_resources.append({ "Section": s, "Unfulfilled Request": u, "Classroom": s.classrooms()[0] })
         self.l_wrong_classroom_type = l_classrooms
         self.l_missing_resources = l_resources
         self.calculated_classes_missing_resources = True
         return [l_classrooms, l_resources]


     def classes_missing_resources(self):
         self._calculate_classes_missing_resources()
         return self.formatter.format_table(self.l_missing_resources, "Unfulfilled Resource Requests", {"headings":["Section", "Unfulfilled Request", "Classroom"]})

     def wrong_classroom_type(self):
         self._calculate_classes_missing_resources()
         return self.formatter.format_table(self.l_wrong_classroom_type, "Classes in wrong classroom type", {"headings": ["Section", "Requested Type", "Classroom"]})

     def teachers_unavailable(self):
         l = []
         for s in self._all_class_sections():
             for t in s.teachers:
                 available = t.getAvailableTimes(s.parent_program, ignore_classes=True)
                 for e in s.get_meeting_times():
                     if e not in available:
                         l.append({"Teacher": t, "Time": e, "Section": s})
         return self.formatter.format_table(l, "Teachers teaching when they aren't available", {"headings": ["Section", "Teacher", "Time"]})

     def teachers_who_like_running(self):
         l = []
         teachers = self.p.teachers()['class_approved'].distinct()
         for teacher in teachers:
             sections = ClassSection.objects.filter(
                 parent_class__in=teacher.getTaughtClassesFromProgram(self.p).filter(status=10).distinct(),status=10).distinct().order_by('meeting_times__start')
             for i in range(sections.count()-1):
                 try:
                     time1 = sections[i+1].meeting_times.all().order_by('start')[0]
                     time0 = sections[i].meeting_times.all().order_by('-end')[0]
                     room0 = sections[i].initial_rooms()[0]
                     room1 = sections[i+1].initial_rooms()[0]
                     if (time1.start-time0.end).total_seconds() < 1200 and sections[i].initial_rooms().count() + sections[i+1].initial_rooms().count() and room0.name != room1.name:
                         l.append({"Teacher": teacher, "Section 1": sections[i], "Section 2": sections[i+1], "Room 1": room0, "Room 2": room1})
                 except BaseException:
                     continue
         return self.formatter.format_table(l, "Teachers who Like Running",
                         {"headings": ["Teacher", "Section 1", "Section 2",
                                       "Room 1", "Room 2"]},
                         help_text="A list of teachers teaching two " +
                         "back-to-back classes (defined as two classes " +
                         "within 20 minutes of each other) in two different " +
                         "locations.")


     def no_overlap_classes(self):
         '''Gets a list of classes from the tag no_overlap_classes, and checks that they don't overlap.  The tag should contain a dict of {'comment': [list,of,class,ids]}.'''
         classes = json.loads(Tag.getProgramTag('no_overlap_classes',program=self.p, default="{}"))
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
         return self.formatter.format_table(bad_classes, "Classes which shouldn't overlap",
                 {'headings': ['Comment', 'Timeblock', 'Classes']},
                 help_text="Given a list of classes that should not overlap, compute which overlap.  This is to be used for example for classes using the same materials which are not tracked by the website, or to check that directors' classes don't overlap.  The classes should be put in the Tag no_overlap_classes, in the format of a dictionary with keys various comments (e.g. 'classes using the Quiz Bowl buzzers') and values as corresponding lists of class IDs."
                 )
                     



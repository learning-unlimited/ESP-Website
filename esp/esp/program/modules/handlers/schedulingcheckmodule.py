from esp.program.models import Program, ClassSection
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.program.models.class_ import open_class_category
from copy import deepcopy
from math import ceil
from esp.cal.models import *
from datetime import date
from esp.web.util.main import render_to_response

#TODO:  data migration to add this module
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
         s.run_diagnostics()
         context = {'checks': s.results}
         return render_to_response(self.baseDir()+'output.html', request, (prog, tl), context)

class SchedulingCheckRunner:
     def __init__(self, program):
          """
          high_school_only and lunch should be lists of indeces of timeslots for the high school
          only block and for lunch respectively
          """
          self.p = program
          self.results = {}
          #self.high_school_blocks = [program.getTimeSlots()[i] for i in high_school_only]
          self.high_school_blocks = self._get_high_school_only()
          #lunch blocks should be a list of lists of blocks that cover lunch
          self.lunch_blocks = self._getLunchByDay()
          self.listed_sections = False

          #TODO:  find a more elegant solution to this problemXo
          #report on setup
          if( len(self.high_school_blocks)>0 ):
               self._format(self.high_school_blocks, 0, "High_School_Only_Blocks")
          if( len(self.lunch_blocks)>0 ):
               self._format(self.lunch_blocks, 0, "Lunch_Blocks")

     #TODO:  refactor this so it's shared with lottery code
     def _getLunchByDay(self):
        import numpy
        #   Get IDs of timeslots allocated to lunch by day
        #   (note: requires that this is constant across days)
        lunch_schedule = numpy.zeros(self.p.num_timeslots())
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

     #TODO: look through email for what other sanity checks should be added on top of these.
     def run_diagnostics(self):
          self.incompletely_scheduled_classes()
          self.multiple_classes_same_room_same_time()
          self.teachers_teaching_two_classes_same_time()
          self.classes_which_cover_lunch()
          self.room_capacity_mismatch()
          self.middle_school_evening_classes()
          self.capacity_by_category()
          self.capacity_by_grade()
          self.admins_teaching_per_timeblock()

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
               self.all_sections = self.p.sections()
               #filter out walkins
               self.all_sections = filter(lambda x: not x.category == open_class_category(), self.all_sections)
               #filter out non-approved classes
               self.all_sections = filter(lambda x: len(x.classrooms()) > 0, self.all_sections)
               self.listed_sections = True
               return self.all_sections

     def _report(self, d, title):
          self._format(d, 0, title)

     def _format(self, d, indent, title):
          if not title in self.results:
               self.results[title] = []
          if type(d) == dict:
               self._format_dict(d, indent, title)
          elif type(d) == list:
               self._format_list(d, indent, title)
          else:
               self._print(self._indent_str(indent) + str(d), title)
     #TODO: rework this to have a format function
     #recursively print the contents of a dictionary
     def _format_dict(self, d, indent, title):
          for key in d:
               self._print(self._indent_str(indent) + str(key), title)
               self._format(d[key], indent+1, title)

     #print the contents of a list, one item on each line
     #TODO:  make this as smart as format list
     def _format_list(self, l, indent, title):
          for i in l:
               self._format(i, indent + 1, title)

     def _indent_str(self, indent):
          return reduce(lambda x,y: x+y, ["   "]*indent, "")

     def _print(self, message, title):
          self.results[title].append(message)
     
     #TODO:  make this also runnable as a script

     #################################################
     #
     #    Diagnostic functions
     #
     #################################################

     def incompletely_scheduled_classes(self):
          problem_classes = []
          for s in self.p.sections():
               mt =  s.get_meeting_times()
               rooms = s.getResources()
               if(len(rooms) != ceil(s.duration)):
                    problem_classes.append(s)
               elif(len(rooms) != len(mt)):
                    problem_classes.append(s)
          self._report(problem_classes, "Classes not completely scheduled:")

     def classes_which_cover_lunch(self):
          l = []
          for s in self._all_class_sections():
               mt =  s.get_meeting_times()
               for lunch in self.lunch_blocks:
                    if not (False in [b in mt for b in lunch]):
                         l.append(s)
          self._report(l, "Classes which are scheduled over lunch")

     #TODO:  test this using data where some teacher is teaching two classes at once
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
                              l.append([t, s, d[mt][t]])
          self._report(l, "Teachers teaching two classes at once")

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
                              l.append([t, r, s, d[t][r]])
          self._report(l, "Double-booked rooms") 
               
     def middle_school_evening_classes(self):
          hso = set(self.high_school_blocks)
          sections = self._all_class_sections()
          #only middle school allowing classes
          sections = filter(lambda x: x.parent_class.grade_min < 9, sections)          
          #only classes in evening timeblocks
          sections = filter(lambda x: len(set(x.get_meeting_times()) & hso) > 0, sections )

          #reporting    
          self._report(sections, "Classes allowing middle school students during the high school only block")
          middle_school_only = filter(lambda x: x.parent_class.grade_max < 9, sections)
          self._report(middle_school_only, "Classe wiht only middle school students during the high school only block")

     def room_capacity_mismatch(self):
          l = []
          lower_reporting_ratio = 0.5
          upper_reporting_ratio = 1.5
          for s in self._all_class_sections():
               r = s.classrooms()
               if len(r) > 0:
                    room = r[0]
                    cls = s.parent_class
                    if room.num_students < lower_reporting_ratio*cls.class_size_max or room.num_students > upper_reporting_ratio*cls.class_size_max:
                         #TODO:  add functionality to format list to be able to do something useful here
                         l.append(str(s) + "\n  class capacity: " + str(cls.class_size_max) + " room capacity: " + str(room.num_students))
          self._report(l, "Class max size/room max size mismatches")


     def capacity_by_category(self):
          #generating a dictionary of class categories
          class_categories =  self.p.class_categories.all().values_list('category', flat=True)
          class_cat_d = {}
          for cat in class_categories:
               if not cat == open_class_category():
                    class_cat_d[cat] = [0, 0]
          def class_category_dict():
               return deepcopy(class_cat_d)

          #populating it with data
          d = self._timeslot_dict(slot=class_category_dict)
          for s in self._all_class_sections():
               mt =  s.get_meeting_times()
               for t in mt:
                    d[t][s.category.category][0] += 1
                    d[t][s.category.category][1] += s.capacity
          
          #convert to tupples for formatting-ness
          for k1 in d:
               for k2 in d[k1]: 
                    d[k1][k2] = tuple(d[k1][k2])
          self._report(d, "Capacity in each block by category.\nGrade: [choices, available slots]")
         
     def capacity_by_grade(self):
          grades =  range(7, 13, 1)
          grades_d = {}
          for grade in grades:
               grades_d[grade] = [0, 0]
          def grade_dict():
               return deepcopy(grades_d)

          #populating it with data
          d = self._timeslot_dict(slot=grade_dict)

          d = self._timeslot_dict(grade_dict)
          for s in self._all_class_sections():
               cls = s.parent_class 
               mt =  s.get_meeting_times()
               for t in mt:
                    for grade in range(cls.grade_min, cls.grade_max + 1, 1):
                         d[t][grade][0] += 1
                         d[t][grade][1] += s.capacity

          dict_title = "Capacity in each block by grade.\nGrade: [choices, available slots]"
          #convert to tupples for formatting-ness
          for k1 in d:
               for k2 in d[k1]: 
                    d[k1][k2] = tuple(d[k1][k2])
          self._report(d, dict_title)

     def admins_teaching_per_timeblock(self):
          d = self._timeslot_dict(lambda: [])
          for s in self._all_class_sections():
               teachers = s.parent_class.teachers()
               admin_teachers = [t for t in teachers if t.isAdministrator()]
               for a in admin_teachers:
                    mt =  s.get_meeting_times()
                    for t in mt:
                         d[t].append(a.username)
          self._report(d, "Admins teaching per timeslot")

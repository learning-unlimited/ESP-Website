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
         results = s.run_diagnostics()
         context = {'checks': results}
         return render_to_response(self.baseDir()+'output.html', request, (prog, tl), context)

#TODO:  does python have some interface equivalent
#Formatter
class RawSCFormatter:
    def format_table(self, l, title, options={}):
        return l

    def format_list(self, l, title, options={}):
        return l

class HTMLSCFormatter:
    #requires: d, a two level dictionary where the the first set of
    #   keys are the headings expected on the side of the table, and
    #   the second set are the headings expected on the top of the table
    def format_table(self, d, title, options={}):
        if type(d) == list:
            return self._format_list_table(d, title, options['headings'])
        else:
            return self._format_dict_table(d, title, options['headings'])

    def format_list(self, l, title):
        output = self._table_title(title, [title])
        for row in l:
            output += self._table_row([row])
        output += "</table>"
        return output

    def _table_start(self):
        output = "<table cellpadding=10 style=\"border: 1px solid black; border-collapse: collapse;\">"
        return output

    def _table_title(self, title, headings):
        output = self._table_start()
        output += "<tr><th colspan=\""+str(len(headings))+"\" align=\"center\">" + str(title) + "</th></tr>"
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
            next_row += "<td>" + str(r) + "</td>"
        next_row += "</tr>"
        return next_row
        
    def _format_list_table(self, d, title, headings):
        output = self._table_title(title, headings)
        output = output + self._table_headings(headings)
        for row in d:
            ordered_row = [row[h] for h in headings]
            output = output + self._table_row(ordered_row) 
        output = output + "</table>"
        return output

    def _format_dict_table(self, d, title, headings):
        output = self._table_title(title, headings)
        output = output + self._table_headings([""] + headings)

        for key, row in d.iteritems():
            ordered_row = [row[h] for h in headings]
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
          self.d_categories = []
          self.d_grades = []

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

     def run_diagnostics(self):
         return [
             self.lunch_blocks_setup(),
             self.high_school_only_setup(),
             self.incompletely_scheduled_classes(),
             self.multiple_classes_same_room_same_time(),
             self.teachers_teaching_two_classes_same_time(),
             self.classes_which_cover_lunch(),
             self.room_capacity_mismatch(),
             self.middle_school_evening_classes(),
             self.classes_by_category(),
             self.capacity_by_category(),
             self.classes_by_grade(),
             self.capacity_by_grade(),
             self.admins_teaching_per_timeblock(),
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
               self.all_sections = self.p.sections()
               #filter out walkins
               self.all_sections = filter(lambda x: not x.category == open_class_category(), self.all_sections)
               #filter out non-approved classes
               self.all_sections = filter(lambda x: len(x.classrooms()) > 0, self.all_sections)
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
          for s in self.p.sections():
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
                    if not (False in [b in mt for b in lunch]):
                         l.append(s)
          return self.formatter.format_list(l, "Classes which are scheduled over lunch")

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
                              l.append({"Teacher": teach, "Timeslot":t, "Section 1": s, "Section 2": d[mt][t]})
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
          return self.formatter.format_list(middle_school_only, "Classe wiht only middle school students during the high school only block")

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

     #for classes_by_category and capacity_by_category
     def _calculate_d_categories(self):
          if len(self.d_categories) > 0:
              return self.d_categories

          self.class_categories =  list(self.p.class_categories.all().values_list('category', flat=True))

          #not regular class categories          
          open_class_cat = open_class_category().category
          if open_class_cat in self.class_categories: self.class_categories.remove(open_class_cat)
          lunch_cat = "Lunch" #TODO:  add a lunch_category function to the program model?
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
                    d_classes[t][s.category.category] += 1
                    d_capacity[t][s.category.category] += s.capacity

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

          self.grades = range(7, 13, 1)
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
               teachers = s.parent_class.teachers()
               admin_teachers = [t for t in teachers if t.isAdministrator()]
               for a in admin_teachers:
                    mt =  s.get_meeting_times()
                    for t in mt:
                         d[t][key_string].append(str(a))
          return self.formatter.format_table(d, "Admins teaching per timeslot", {"headings":[key_string]})


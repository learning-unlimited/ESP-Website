from esp.program.models import Program, ClassSection


def do_checks(prog_id):
     prog = Program.objects.filter(id=prog_id)[0];
     class_categories(prog)
     class_room_capacity_mismatch(prog)
     double_scheduled_teachers(prog)
     non_available_teachers(prog)
     classes_by_min_grade(prog)
     classes_scheduled_over_lunch(prog)
     admins_teaching_by_timeblock(prog)

#prints number of classes in each category for each timeblock
def class_categories(splash):
     d = {}
     for cls in splash.classes():
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               for t in mt:
                    if not t in d:
                         d[t] = {}
                         if not cls.category in d[t]:
                              d[t][cls.category] = 0
                              d[t][cls.category] += 1
     #print them
     for t in d:
          print t
          for c in d[t]:
               print "    ", c, d[t][c]


#prints classes which have capacities very different from those of their classrooms
def class_room_capacity_mismatch(splash):
     print "\n\n\n Class capacity mismatches:  classname: class max/room match"
     for cls in splash.classes():
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               r = s.classrooms()
               if len(r) > 0:
                    room = r[0]
                    if room.num_students < .5*cls.class_size_max or room.num_students > 1.5*cls.class_size_max:
                         print str(s) + ":" + str(cls.class_size_max) + "/" + str(room.num_students)



#gives number of classes with each min grade in each timeblock
def classes_by_min_grade(splash):
     print "classes by min grade"
     d = {}
     for cls in splash.classes():
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               for t in mt:
                    if not t in d:
                         d[t] = {}
                    if not cls.grade_min in d[t]:
                         d[t][cls.grade_min] = 0
                    d[t][cls.grade_min] += 1

     #print them
     for t in d:
          print t
          for c in d[t]:
               print "    ", c, d[t][c]

#check for teacher
def non_available_teachers(splash):
     print "Teachers not available during their classes"
     d = {}
     for cls in splash.classes():
          teachers = cls.teachers()
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               for t in mt:
                    for teach in teachers:
                         if not t in teach.getAvailableTimes(splash):
                              print teach, cls, mt

#teachers scheduled to teach two classes at the same time
def double_scheduled_teachers(splash):
     print "\n\nTeachers scheduled to teach multiple classes at once"
     d = {}
     for cls in splash.classes():
          teachers = cls.teachers()
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               for t in mt:
                    for teach in teachers:
                         classes = teach.getTaughtClasses(program=splash)
                         for tc in classes:
                              if(tc == cls):
                                   continue
                              secs = ClassSection.objects.filter(parent_class=tc.id)
                              for sec in secs:
                                   timeblocks = sec.get_meeting_times()
                                   if t in timeblocks:
                                        print teach, t, cls, tc

def high_school_only_block(splash):
     hso = splash.getTimeSlots()[9:12]
     for cls in splash.classes():
          teachers = cls.teachers()
          sections = ClassSection.objects.filter(parent_class=cls.id)
          if cls.grade_min < 9:
               for s in sections:
                    mt =  s.get_meeting_times()
                    for m in mt:
                         if m in hso:
                              print s, m

def classes_scheduled_over_lunch(splash):
     lunch = splash.getTimeSlots()[3:5]
     for cls in splash.classes():
          teachers = cls.teachers()
          sections = ClassSection.objects.filter(parent_class=cls.id)
          if cls.grade_min < 9:
               for s in sections:
                    mt =  s.get_meeting_times()
                    if lunch[0] in mt and lunch[1] in mt:
                         print s

def admins_teaching_by_timeblock(splash):
     print "\n\n\nAdmins teaching in each timeblock"
     d = {}
     for cls in splash.classes():
          teachers = cls.teachers()
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               for t in mt:
                    if not t in d:
                         d[t] = []
                    for teach in teachers:
                         if teach.isAdministrator():
                              d[t].append(teach)
     for t in d:
          print t, "\n", d[t], "\n\n"


def classes_with_no_classrooms(splash):
     print "\n\n\n Classes not in rooms"
     for cls in splash.classes():
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               r = s.classrooms()
               if len(r) == 0:
                    print s

def classes_with_no_times(splash):
     print "\n\n\n Classes with no times"
     for cls in splash.classes():
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               r = s.classrooms()
               mt = s.get_meeting_times()
               if len(r) == 0:
                    print s

#I think this is double scheduled rooms but I'm not sure
def douhle_scheduled(splash):
     print "\n\n\nIf anything is printed below this then something is wrong but I don't know what"
     d = {}
     for cls in splash.classes():
          teachers = cls.teachers()
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               rooms = s.classrooms()
               if len(rooms) > 0:
                    r = rooms[0]
               for t in mt:
                    if not t in d:
                         d[t] = {}
                    if not r in d[t]:
                         d[t][r] = s
                    else:
                         print d[t][r], s


def under_scheduled(splash):
     print "\n\n\nClasses scheduled for fewer timeslots than it's length"
     for cls in splash.classes():
          sections = ClassSection.objects.filter(parent_class=cls.id)
          for s in sections:
               mt =  s.get_meeting_times()
               rooms = s.getResources()
               if(len(rooms) != math.ceil(cls.duration) and len(rooms) > 0):
                    print s

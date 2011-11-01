from esp.program.models import Program, Class, ClassSection

splash = Program.objects.filter(id=74)[0]

d = {}
for cls in splash[0].classes():
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
         mt =  s.get_meeting_times()
         for t in mt:
             if not t in d:
                 d[t] = {}
             if not cls.category in d[t]:
                 d[t][cls.category] = 0
             d[t][cls.category] += 1


f = open("oct_11_scheduling_checks.txt", 'w')
for cls in splash.classes():
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
          r = s.classrooms()
          if len(r) > 0:
               room = r[0]
               if room.num_students < .5*cls.class_size_max or room.num_students > 1.5*cls.class_size_max:
                         f.write(str(s)+ "\n")
                         f.write("class capacity: " + str(cls.class_size_max)+ "\n")
                         f.write("room capacity: " + str(room.num_students)+ "\n")




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

teachers = [ESPUser(x) for x in prog.teachers()['class_approved']]
for teacher in teachers:
    available_times = teacher.getAvailableTimes(prog)
    for timeslot in available_times:
        file.write('  <available block=%d />\n' % timeslot.id)
    file.write('</teacher>\n')


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

lunch = splash.getTimeSlots()[3:5]

for cls in splash.classes():
     teachers = cls.teachers()
     sections = ClassSection.objects.filter(parent_class=cls.id)
     if cls.grade_min < 9:
          for s in sections:
               mt =  s.get_meeting_times()
               if lunch[0] in mt and lunch[1] in mt:
                    print s

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
     print t, d[t]


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


f = open("oct_11_scheduling_checks.txt", 'w')
for cls in splash.classes():
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
          r = s.classrooms()
          if len(r) == 0:
               print s



for cls in splash.classes():
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
          r = s.classrooms()
          mt = s.get_meeting_times()

          if len(r) == 0:
               print s


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

for cls in splash[0].classes():
     teachers = cls.teachers()
     i = 0
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
         mt =  s.get_meeting_times()
         rooms = s.getResources()
         if len(rooms) > 0:
            r = rooms[0]
            for t in mt:
                if not t in d:
                    d[t] = {}
                if not r in d[t]:
                    d[t][r] = s
                else:
                    print d[t][r], s
         else:
              i = i +1
print i




d = {}
for cls in splash[0].classes():
     teachers = cls.teachers()
     i = 0
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
         f.write(str(s.id)+ "\n")
         mt =  s.get_meeting_times()
         rooms = s.getResources()
         f.write(str(len(rooms))+ "\n")
         if len(rooms) > 0:
            r = rooms[0]
            f.write(str(r)+ "\n")
            for t in mt:
                if not t in d:
                    d[t] = {}
                if not r in d[t]:
                    d[t][r] = s
                else:
                    if d[t][r] != s:
                         print d[t][r], s
         else:
              i = i +1


for cls in splash[0].classes():
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
          mt =  s.get_meeting_times()
          rooms = s.getResources()
          if(len(rooms) != math.ceil(cls.duration) and len(rooms) > 0):
               print s


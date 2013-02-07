from esp.program.models import *

splash = Program.objects.filter(id=74)[0]

d = {}
for cls in splash.classes():
     teachers = cls.teachers()
     sections = ClassSection.objects.filter(parent_class=cls.id)
     for s in sections:
         mt =  s.get_meeting_times()
         for t in mt:
              if not t in d:
                   d[t] = {}
              rooms = s.classrooms()
              if len(rooms) > 0:
                   r = rooms[0]
                   if not r in d[t]:
                        d[t][r] = s
                   else:
                        print d[t][r], s

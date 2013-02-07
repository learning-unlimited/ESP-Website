from esp.program.models import Program, ClassSection
prog = Program.objects.get(pk=74)
teachers = prog.teachers()['class_approved'].distinct()

for teacher in teachers:
   sections = ClassSection.objects.filter(parent_class__in=teacher.getTaughtClassesFromProgram(prog).filter(status=10).distinct(),status=10).distinct().order_by('meeting_times__start')
   for i in range(sections.count()-1):
       try:
           time1 = sections[i+1].meeting_times.all().order_by('start')[0]
           time0 = sections[i].meeting_times.all().order_by('-end')[0]
           if (time1.start-time0.end).seconds < 1200 and sections[i].initial_rooms().count() + sections[i+1].initial_rooms().count() and sections[i].initial_rooms()[0].name != sections[i+1].initial_rooms()[0].name:
               print "%s \t %s \t %s \t %s,\t\t %s \t %s" % (teacher.username, sections[i].emailcode(), sections[i].initial_rooms()[0].name, time0.end, sections[i+1].emailcode(), sections[i+1].initial_rooms()[0].name)
       except BaseException:
           continue

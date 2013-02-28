from esp.program.models import *
verbose = True

def _getLunchByDay(prog):
    import numpy
    #   Get IDs of timeslots allocated to lunch by day
    #   (note: requires that this is constant across days)
    lunch = [[],[]]
    timeslots = Event.objects.filter(meeting_times__parent_class__parent_program=prog).order_by('start').distinct()
    for t in timeslots:
        if t.start.hour >= 12 and t.end.hour <=13:
            lunch[t.start.day-17].append(t)
    return lunch

def teachers_teaching_over_lunch(prog, lunch):
    l = []
    teachers = prog.teachers()['class_approved'].distinct()
    for teacher in teachers:
        sections = ClassSection.objects.filter(
            parent_class__in=teacher.getTaughtClassesFromProgram(prog).filter(status=10).distinct(),status=10).distinct().order_by('meeting_times__start')
        meeting_times = []
        for s in sections:
            for m in s.meeting_times.all():
                meeting_times.append(m)

        for lu in lunch:
            if verbose: print lu
            if not (False in [b in meeting_times for b in lu]):
                if lu != []: l.append((teacher, lu, teacher.getTaughtClassesFromProgram(prog)))
        
    return l


prog = Program.objects.get(id=88)
if verbose: print prog
lunch = _getLunchByDay(prog)
print lunch
for item in teachers_teaching_over_lunch(prog, lunch):
    print item

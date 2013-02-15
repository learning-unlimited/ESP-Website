from esp.program.models import *

p = Program.objects.filter(id=89)[0]	# Spring HSSP 2013

not_all_timeblocks = set()
only_one_preference = set()

for s in p.students()['lotteried_students']:
    student_registrations = StudentRegistration.objects.filter(section__parent_class__parent_program=p,end_date__gt=datetime.now(),user=s).distinct()
    student_sections = [r.section for r in student_registrations]
    
    reg_times = {}
    for sec in student_sections:
        times = sec.get_meeting_times()
        for time in times:
            reg_times[time] = reg_times.get(time, 0) + 1
    
    if len(reg_times) < 4:
        not_all_timeblocks.add(s)
    
    for time in times:
        if reg_times[time] is 1:
            only_one_preference.add(s)

print "\nStudents who haven't signed up for all timeblocks:"
print ",\n".join([user.email for user in (not_all_timeblocks - only_one_preference)])
print "\nStudents who have only one preference for at least one timeblock:"
print ",\n".join([user.email for user in (only_one_preference - not_all_timeblocks)])
print "\nStudents with BOTH of the above (omitted from the above lists):"
print ",\n".join([user.email for user in only_one_preference.intersection(not_all_timeblocks)])

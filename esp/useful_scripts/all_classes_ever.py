from esp.program.models import Program, ClassSubject

programs = Program.objects.order_by('id')
all_subjects = ClassSubject.objects.filter(status__gt=0, sections__status__gt=0, sections__meeting_times__isnull=False, sections__resourceassignment__isnull=False).exclude(category__category__iexact="Lunch").distinct() # Returns a QuerySet of all ClassSubjects that are approved (and have an approved section), that have a scheduled section, and that aren't in the "Lunch" category
class_title_delimeter = ' ||| '
f = open('all_classes_ever.txt','w')
f.write("Class Title Delimeter: '%s'\n\n\n\n\n" % class_title_delimeter)

def to_ascii(s):
    try:
       return str(s).strip().decode('ascii')
    except Exception:
       return ""

for program in programs:

    subjects = all_subjects.filter(parent_program=program)
    titles = subjects.values_list('title',flat=True).distinct()
    if titles:
        titles = list(titles)
        titles = map(to_ascii,titles)
        titles = class_title_delimeter.join(titles)
        f.write('%s\n\n\t%s\n\n\n\n' % (program, titles))

f.close()

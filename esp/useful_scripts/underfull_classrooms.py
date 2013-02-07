from esp.program.models import *
from esp.program.models.class_ import open_class_category

f = open('/esp/esp/useful_scripts/underful_classrooms.csv', 'w')

exceptions = ["H6792s1", "H6792s2", "A6783s1", "A6783s2", ]

def underfull_classrooms(prog):
    all_sections = prog.sections()
    #filter out walkins
    all_sections = filter(lambda x: not x.category == open_class_category(), all_sections)

    l = []
    for s in all_sections:
        r = s.classrooms()
        if len(r) > 0:
            room = r[0]
            cls = s.parent_class
            if room.num_students > cls.class_size_max and (room.num_students<cls.class_size_max*2 or cls.class_size_max > 99):
                l.append(s)

    teacher_classes = {}
    for s in l:
        teachers = s.parent_class.teachers()
        for t in teachers:
            if not t in teacher_classes:
                teacher_classes[t] = []
            teacher_classes[t].append(s)

    for t in teacher_classes:
        classes = "\""
        for s in teacher_classes[t]:
            classes = classes + s.emailcode() + " "+ s.title() + ": Current class cap: " + str(s.parent_class.class_size_max) + ", Room size: " + str(s.classrooms()[0].num_students) + "\n"
        classes = classes + "\""
        writeval = t.email + "," + classes
        #some characters teachers put in titles don't write nicely
        writeval = writeval.replace(u'\u2019', '\'')
        writeval = writeval.replace(u'\xe9', 'e')
        print writeval
        f.write(writeval)

prog = Program.objects.get(id=85)
underfull_classrooms(prog)

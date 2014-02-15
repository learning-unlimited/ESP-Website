
from script_setup import *

PROG = 105

prog = Program.objects.get(id=PROG)

walkins = ClassSection.objects.filter(parent_class__parent_program__id=PROG, parent_class__category=prog.open_class_category)

for w in walkins:
    w.duration += 1
    w.save()

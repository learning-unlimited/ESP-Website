from esp.program.models import *

prog_id = 85

prog = Program.objects.get(id=prog_id)
classes = ClassSubject.objects.filter(grade_max__gte=10, parent_program__id=prog.id)
for c in classes:
    if c.category.symbol != "W":
        if c.class_size_max >= 100:
            print c.title()


progs = Program.objects.all()
for p in progs:
    if str(p).startswith("Splash") or str(p).startswith("Spark") or str(p).startswith("HSSP"):
        if p.id > 70 and p.id < 85:
            recent.append(p)

for p in recent:
    t = ClassSubject.objects.filter(grade_max__lte=9, parent_program__id=p.id)
    for c in t:
        teachers.append(teach)
        if str(c).find("test") < 0 and str(c).find("Test") < 0:
            if len(c.teachers()) > 0:
                if not c.teachers()[0].isAdministrator():
                    print str(c.teachers()[0].email) + ","


from esp.program.models import *

splash = Program.objects.get(id=85)
bismoth = ClassSubject.objects.filter(id=6253)
sections = ClassSection.objects.filter(parent_class=bismoth)

for i in range(3):
    registrations = StudentRegistration.objects.filter(section=sections[i])
    for r in registrations:
        for s in [sections[i+3], sections[i+6]]:
            print r.pk
            r.pk = None
            r.section = s
            r.save()
            print r.pk

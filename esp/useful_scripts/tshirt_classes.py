from esp.program.models import *
p = Program.objects.filter(id=85)[0]

i = 0
for c in p.classes():
    if i >=75:
        break
    i = i + 1
    print c.title()

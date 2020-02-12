from esp.program.models import *
from esp.dbmail.models import PlainRedirect

list_name = 'sp10-parents'
splash = Program.objects.get(id=11)
sl = splash.students()['classreg']

outfile = open('stanford_parents_sp10.csv', 'w')

outfile.write('"ID","Last Name","First Name","Student email","Parent email"\n')

PlainRedirect.objects.filter(original=list_name).delete()

for s in sl:
    fn = s.first_name
    ln = s.last_name
    id = s.id
    p = ESPUser(s).getLastProfile()
    if p.contact_user:
        ea = p.contact_user.e_mail
    else:
        ea = ''
    if p.contact_guardian:
        pe = p.contact_guardian.e_mail
        le, created = PlainRedirect.objects.get_or_create(original=list_name, destination=pe)
    else:
        pe = ''
    outfile.write('"%s","%s","%s","%s","%s"\n' % (id, ln.encode('ascii', 'replace'), fn.encode('ascii', 'replace'), ea.encode('ascii', 'replace'), pe.encode('ascii', 'replace')))

outfile.close()
print 'Wrote to %s' % outfile
print 'Created %d list entries' % PlainRedirect.objects.filter(original=list_name).count()



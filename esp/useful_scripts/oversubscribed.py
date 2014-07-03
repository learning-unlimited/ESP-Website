#Exports as csv file with how oversubscribed a class is.
# %run filename to run

from esp.program.models import Program
import csv


PROGRAM_NAME = "Splash! 2013"
DIRECTORY = "/home/shulinye/" #where you want the file saved.

cls = Program.objects.get(name=PROGRAM_NAME).classes()

csvwriter = csv.writer(open(DIRECTORY+"oversubscribed.csv", "wb"), delimiter='|')

csvwriter.writerow(["Name", "Blocks", "# Students Interested", "Max Size", "#_Students/Size"])

for c in cls:
    n = c.studentsubjectinterest_set.all().count()
    m = c.max_students()

    csvwriter.writerow([c.title.encode('ascii', 'ignore'), (', '.join(c.prettyblocks())).encode('ascii', 'ignore'), n, m, n*1.0/(m+1)])

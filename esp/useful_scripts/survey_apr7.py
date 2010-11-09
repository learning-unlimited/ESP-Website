from esp.program.models import *
from esp.survey.models import *
from esp.datatree.models import *

splash = Program.objects.get(id=11)
auri = splash.anchor.uri

# create survey
survey, created = Survey.objects.get_or_create(name = 'Splash Student Survey', anchor=splash.anchor, category='learn')
survey.save()
print survey

infile = open('/home/pricem/survey_learn_out.txt')

data = infile.read()
entries = data.split('\n.\n')[:-1]
for entry in entries:
    qlist = entry.split('":"')
    seq = int(qlist[0])
    anchor = DataTree.get_by_uri(splash.anchor.uri + qlist[1])
    pv = qlist[2]
    qt = QuestionType.objects.get(id=qlist[3])
    name = qlist[4]
    q, c = Question.objects.get_or_create(survey=survey, name=name, question_type=qt, _param_values=pv, anchor=anchor, seq=seq)
    print q
    print q.__dict__
    q.save()

infile.close()

from esp.program.models import *
from esp.survey.models import *
from esp.datatree.models import *


splash = Program.objects.get(id=47)
auri = splash.anchor.uri
aulen = len(auri)

def save_survey(survey, filename):
    print survey

    outfile = open(filename, 'w')

    questions = survey.questions.order_by('id')

    for q in questions:
        str_fragments = []
        str_fragments.append('%d' % q.seq)
        str_fragments.append(q.anchor.uri[aulen:])
        str_fragments.append(q._param_values)
        str_fragments.append('%d' % q.question_type_id)
        str_fragments.append(q.name)
        outfile.write('":"'.join(str_fragments))
        outfile.write('\n.\n')

    outfile.close()

    #outfile = open('/home/pricem/survey_out.txt', 'w')
save_survey(survey = Survey.objects.get(anchor=splash.anchor, category='learn'), filename='E:/projects/lu_sites/esp_mit/spark10_learn_out.txt')
save_survey(survey = Survey.objects.get(anchor=splash.anchor, category='teach'), filename='E:/projects/lu_sites/esp_mit/spark10_teach_out.txt')

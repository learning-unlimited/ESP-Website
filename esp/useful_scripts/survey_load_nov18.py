from esp.program.models import *
from esp.survey.models import *
from esp.datatree.models import *

def load_survey(program, survey_name, category, input_file):

    # create survey
    survey, created = Survey.objects.get_or_create(name=survey_name, anchor=program.anchor, category=category)
    survey.save()
    print survey

    auri = program.anchor.uri

    infile = open(input_file)

    data = infile.read()
    entries = data.split('\n.\n')[:-1]
    for entry in entries:
        qlist = entry.split('":"')
        seq = int(qlist[0])
        anchor = DataTree.get_by_uri(auri + qlist[1])
        pv = qlist[2]
        qt = QuestionType.objects.get(id=qlist[3])
        name = qlist[4]
        q, c = Question.objects.get_or_create(survey=survey, name=name, question_type=qt, _param_values=pv, anchor=anchor, seq=seq)
        print q
        print q.__dict__
        q.save()

    infile.close()

splash = Program.objects.get(id=65)
load_survey(splash, "Splash! 2010 Student Survey", "learn", "/home/price/spark10_learn_out.txt")
load_survey(splash, "Splash! 2010 Teacher Survey", "teach", "/home/price/spark10_teach_out.txt")

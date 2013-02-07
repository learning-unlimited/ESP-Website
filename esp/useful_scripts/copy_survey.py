from esp.program.models import *
from esp.survey.models import *
from esp.datatree.models import *

#replace this with actual creation of a new survey
new_survey_id = 34
new_survey = Survey.objects.filter(id=new_survey_id)[0]
new_survey_anchor = new_survey.anchor
new_survey_class_anchor = DataTree.objects.filter(uri=new_survey_anchor.uri + "/Classes")[0]
#replace this with code for retreiving an old survey by program
old_survey_id = 26
old_survey = Survey.objects.filter(id=old_survey_id)[0]

print new_survey_anchor
print new_survey_class_anchor

#delete other questions already on this survey.  Once we change the creation behavior we can delete this
Question.objects.filter(survey=new_survey).delete()

#copy questions
questions = Question.objects.filter(survey=old_survey)
for old_q in questions:
    #reformat param values
    pv = old_q.param_values
    final_pv = ""
    for v in pv:
        final_pv = final_pv + v + "|"
    final_pv = final_pv[:-1] #delete final pipe

    #retreive anchor- either the program or the program's classes
    anchor = new_survey_anchor
    if old_q.anchor.uri.endswith("Classes"):
        anchor = new_survey_class_anchor

    new_q, c =  Question.objects.get_or_create(survey=new_survey, name=old_q.name, question_type=old_q.question_type, _param_values=final_pv, anchor=anchor, seq=old_q.seq)
    new_q.save()

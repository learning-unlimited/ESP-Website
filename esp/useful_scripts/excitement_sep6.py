#!/usr/bin/env python

from esp.survey.models import *

def get_excitement(question_id, threshold):
    question = Question.objects.get(id=question_id)
    survey = question.survey
    program = Program.objects.get(anchor=survey.anchor)
    responses = survey.surveyresponse_set.all()
    num_responses = responses.count()
    num_answers = 0
    num_excited_one = 0
    num_excited_all = 0
    num_classes_taken = 0
    for response in responses:
        #   print 'Response #%d' % response.id
        answers = response.answers.filter(question__id=question_id)
        if answers.count() > 0:
            excited_one = False
            excited_all = True
            for answer in answers:
                #   print '%s: %s' % (answer.anchor.uri, answer.value)
                value = int(answer.value.strip(':_| '))
                if value >= threshold:
                    excited_one = True
                else:
                    excited_all = False
            num_answers += 1
            if excited_one: num_excited_one += 1
            if excited_all:
                num_excited_all += 1
                num_classes_taken += answers.count()
    print '%s: %s' % (program.niceName(), question.name)
    print '    Threshold: %d or higher' % threshold
    print ' -> Total number of responses: %d (%d answered this question)' % (num_responses, num_answers)
    if num_answers > 0:
        print ' -> Number of responses above threshold for one or more classes: %d/%d (%.2f%%)' % (num_excited_one, num_answers, float(num_excited_one) / num_answers * 100)
        print ' -> Number of responses above threshold for all classes rated: %d/%d (%.2f%%); avg %.2f classes/student' % (num_excited_all, num_answers, float(num_excited_all) / num_answers * 100, float(num_classes_taken) / num_excited_all)

"""
Example usage:
questions_mit = [21, 109, 240, 368, 514, 636]
questions_stanford = [21, 194, 240, 365, 487]

for id in questions_stanford:
    get_excitement(id, 4)
"""

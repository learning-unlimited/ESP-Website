__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""

from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.survey.models import Survey, Question, QuestionType, SurveyResponse, Answer
from esp.users.models import Record

import random
import re

class SurveyTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            } )
        super(SurveyTest, self).setUp(*args, **kwargs)
        
        self.add_student_profiles()
        self.schedule_randomly()

        #   Make all modules non-required for now, so we don't have to be shown required pages
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

    def test_survey(self):
        #   Pick a student and sign them up for a class
        student = random.choice(self.students)
        sec = random.choice(self.program.sections())
        sec.preregister_student(student)
        self.failUnless( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
    
        #   Access the survey page - there should be no surveys and we should get an error
        response = self.client.get('/learn/%s/survey' % self.program.url)
        self.assertEqual(response.status_code, 500)
        self.assertIn('no such survey', response.content)
        
        #   Create a survey
        (survey, created) = Survey.objects.get_or_create(name='Test Survey', program=self.program, category='learn')
        (qtype, created) = QuestionType.objects.get_or_create(name='yes-no response')
        (question_base, created) = Question.objects.get_or_create(survey=survey, name='Question1', question_type=qtype, per_class=False, seq=0)
        (question_perclass, created) = Question.objects.get_or_create(survey=survey, name='Question2', question_type=qtype, per_class=True, seq=1)

        #   Make sure the user is marked as not having completed it
        self.assertFalse(Record.user_completed(student, 'student_survey', self.program))

        #   Now we should be able to access the survey
        response = self.client.get('/learn/%s/survey' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Question1', response.content)
        
        #   Check that there is a field to select a class for each timeslot
        for timeslot in self.program.getTimeSlots():
            self.assertIn('attendance_%d' % (timeslot.id), response.content)
        
        #   Fill out the survey with some arbitrary answers
        sec_timeslot = sec.get_meeting_times()[0]
        form_settings = {
            'attendance_%d' % sec_timeslot.id: '%s' % sec.id,
            'question_%d' % question_base.id: 'Yes',
            'question_%d_%d' % (question_perclass.id, sec_timeslot.id): 'No',
        }
        
        #   Submit the survey
        response = self.client.post('/learn/%s/survey' % self.program.url, form_settings, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertTrue(response.redirect_chain[0][0].endswith('/learn/%s/survey?done' % self.program.url))
        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertIn('have been saved', response.content)
        
        #   Check that we have a SurveyRecord with the right answers associated with it
        self.assertEqual(SurveyResponse.objects.filter(survey=survey).count(), 1)
        record = SurveyResponse.objects.filter(survey=survey)[0]
        self.assertEqual(Answer.objects.filter(question=question_base).count(), 1)
        answer_base = Answer.objects.filter(question=question_base)[0]
        self.assertEqual(answer_base.answer, 'Yes')
        self.assertEqual(answer_base.target, self.program)
        self.assertEqual(Answer.objects.filter(question=question_perclass).count(), 1)
        answer_perclass = Answer.objects.filter(question=question_perclass)[0]
        self.assertEqual(answer_perclass.answer, 'No')
        self.assertEqual(answer_perclass.target, sec)
        
        #   Check that the student is marked as having filled out the survey
        self.assertTrue(Record.user_completed(student, 'student_survey', self.program))
        
        #   Check that we get an error if we try to visit the survey again
        response = self.client.get('/learn/%s/survey' % self.program.url)
        self.assertEqual(response.status_code, 500)
        self.assertIn('already filled out', response.content)
        
        


__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
  Email: web-team@learningu.org
"""

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.survey.models import Survey, Question, QuestionType

class SurveyManagementTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        pm = ProgramModule.objects.get(handler='SurveyManagement')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.admin = self.admins[0]
        self.base_url = '%ssurveys/manage' % self.program.get_manage_url()

    def test_survey_manage_page_loads(self):
        """Test that survey management page loads for admin."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_create_survey(self):
        """Test that a new survey can be created."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        initial_count = Survey.objects.filter(
            program=self.program
        ).count()
        response = self.client.post(
            self.base_url + '?obj=survey',
            {
                'name': 'Test Survey',
                'category': 'learn',
            }
        )
        new_count = Survey.objects.filter(
            program=self.program
        ).count()
        self.assertGreater(new_count, initial_count)

    def test_create_question(self):
        """Test that a new question can be created."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn'
        )
        qt = QuestionType.objects.first()
        initial_count = Question.objects.filter(
            survey=survey
        ).count()
        response = self.client.post(
            self.base_url + '?obj=question',
            {
                'name': 'Test Question',
                'survey': survey.id,
                'question_type': qt.id,
                'seq': 1,
                'per_class': False,
            }
        )
        new_count = Question.objects.filter(
            survey=survey
        ).count()
        self.assertGreaterEqual(new_count, initial_count)

    def test_invalid_operation(self):
        """Test that invalid operations are handled gracefully."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        response = self.client.get(
            self.base_url + '?obj=survey&op=invalid&id=999'
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_survey(self):
        """Test that a survey can be deleted."""
        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password'
            ),
            "Couldn't log in as admin"
        )
        survey = Survey.objects.create(
            name='Survey To Delete',
            program=self.program,
            category='learn'
        )
        response = self.client.post(
            self.base_url + '?obj=survey&op=delete&id=%s' % survey.id,
            {'delete_confirm': 'yes'}
        )
        self.assertFalse(
            Survey.objects.filter(id=survey.id).exists()
        )

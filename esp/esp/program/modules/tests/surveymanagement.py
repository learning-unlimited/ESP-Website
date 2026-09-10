"""
Unit tests for SurveyManagement (surveymanagement.py).

"""
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.survey.models import Survey, Question, QuestionType


class SurveyManagementTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 1, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.module = self.get_module_obj('SurveyManagement')
        self.qtype, _ = QuestionType.objects.get_or_create(
            name='yes-no response',
            defaults={'is_numeric': False, 'is_countable': False},
        )

    def _main_url(self):
        return self.get_module_url('manage', 'surveys')

    def _manage_url(self):
        return self._main_url() + '/manage'

    def test_main_page_renders_for_admin(self):
        self.login_as('admin')
        response = self.assert_view_ok(self._main_url())
        self.assertIn('surveys', response.context)
        self.assertIn('counts', response.context)

    def test_student_cannot_access(self):
        self.login_as('student')
        response = self.client.get(self._main_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    def test_manage_page_renders_with_dummy_context(self):
        self.login_as('admin')
        response = self.assert_view_ok(self._manage_url())
        self.assertIn('classes', response.context)
        self.assertIn('section', response.context)
        self.assertIn('survey_form', response.context)
        self.assertIn('question_form', response.context)

    def test_create_survey(self):
        self.login_as('admin')
        response = self.client.post(
            self._manage_url() + '?obj=survey',
            {'name': 'End of Program Survey', 'category': 'learn'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Survey.objects.filter(
                name='End of Program Survey', program=self.program, category='learn'
            ).exists()
        )

    def test_edit_survey(self):
        survey = Survey.objects.create(
            name='Old Name', program=self.program, category='teach'
        )
        self.login_as('admin')
        response = self.client.post(
            self._manage_url() + '?obj=survey&id=%s' % survey.id,
            {'name': 'New Name', 'category': 'teach', 'survey_id': str(survey.id)},
        )
        self.assertEqual(response.status_code, 200)
        survey.refresh_from_db()
        self.assertEqual(survey.name, 'New Name')

    def test_create_question(self):
        survey = Survey.objects.create(
            name='Q Survey', program=self.program, category='learn'
        )
        self.login_as('admin')
        response = self.client.post(
            self._manage_url() + '?obj=question',
            {
                'survey': str(survey.id),
                'name': 'Did you enjoy the program?',
                'question_type': str(self.qtype.id),
                'per_class': False,
                'seq': '1',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Question.objects.filter(
                survey=survey, name='Did you enjoy the program?'
            ).exists()
        )

    def test_delete_survey_with_confirm(self):
        survey = Survey.objects.create(
            name='To Delete', program=self.program, category='learn'
        )
        Question.objects.create(
            survey=survey, name='Q1', question_type=self.qtype, seq=1
        )
        self.login_as('admin')
        response = self.client.post(
            self._manage_url() + '?obj=survey&op=delete&id=%s' % survey.id,
            {'delete_confirm': 'yes'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Survey.objects.filter(id=survey.id).exists())

    def test_delete_survey_confirmation_page(self):
        survey = Survey.objects.create(
            name='Confirm Delete', program=self.program, category='learn'
        )
        self.login_as('admin')
        response = self.client.get(
            self._manage_url() + '?obj=survey&op=delete&id=%s' % survey.id
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'program/modules/surveymanagement/survey_delete.html'
        )
        self.assertTrue(Survey.objects.filter(id=survey.id).exists())

    def test_csv_export(self):
        survey = Survey.objects.create(
            name='Export Me', program=self.program, category='learn'
        )
        Question.objects.create(
            survey=survey, name='Rate it', question_type=self.qtype, seq=1
        )
        self.login_as('admin')
        url = self._main_url() + '/csv_export?survey_id=%s' % survey.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('Rate it', content)
        self.assertIn('question_text', content)

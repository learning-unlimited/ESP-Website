"""
Tests for esp.survey.admin
Source: esp/esp/survey/admin.py

Tests SurveyAdmin import_questions action.
"""
import io

from django.contrib.auth.models import Group, User
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from esp.program.models import Program
from esp.survey.models import Survey, QuestionType, Question
from esp.survey.admin import SurveyAdmin


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class SurveyAdminImportTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        
        # Create test user
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password'
        )
        
        # Create test program and survey
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        
        # Create question types
        self.qt_yesno = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.qt_rating = QuestionType.objects.create(
            name='Rating',
            _param_names='min|max',
            is_numeric=True,
            is_countable=True,
        )
        
        # Setup admin
        self.site = AdminSite()
        self.admin = SurveyAdmin(Survey, self.site)
        self.factory = RequestFactory()
    
    def _create_request(self, method='GET', data=None, files=None):
        """Helper to create a request with session and messages."""
        if method == 'GET':
            request = self.factory.get('/admin/survey/survey/')
        else:
            request = self.factory.post('/admin/survey/survey/', data=data or {}, files=files or {})
        
        request.user = self.user
        
        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add messages
        setattr(request, '_messages', FallbackStorage(request))
        
        return request
    
    def test_import_questions_action_exists(self):
        """Test that import_questions action is registered."""
        self.assertIn('import_questions', self.admin.actions)
    
    def test_import_questions_requires_single_survey(self):
        """Test that import action requires exactly one survey."""
        # Create another survey
        survey2 = Survey.objects.create(
            name='Test Survey 2',
            program=self.program,
            category='teach',
        )
        
        # Try with multiple surveys
        queryset = Survey.objects.filter(id__in=[self.survey.id, survey2.id])
        request = self._create_request()
        
        response = self.admin.import_questions(request, queryset)
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
    
    def test_import_questions_displays_form(self):
        """Test that import action displays the form."""
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request()
        
        response = self.admin.import_questions(request, queryset)
        
        # Should render template
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Import Questions', response.content)
    
    def test_import_questions_with_valid_csv(self):
        """Test importing questions from valid CSV."""
        csv_content = """question_name,question_type,param_values,per_class,sequence
Did you enjoy the program?,Yes/No,,false,1
Rate the program,Rating,1|5,false,2"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'
        
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request(
            method='POST',
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        
        response = self.admin.import_questions(request, queryset)
        
        # Should redirect after successful import
        self.assertEqual(response.status_code, 302)
        
        # Verify questions were created
        questions = Question.objects.filter(survey=self.survey)
        self.assertEqual(questions.count(), 2)
        
        # Verify first question
        q1 = questions.get(name='Did you enjoy the program?')
        self.assertEqual(q1.question_type.name, 'Yes/No')
        self.assertEqual(q1.seq, 1)
        self.assertFalse(q1.per_class)
        
        # Verify second question
        q2 = questions.get(name='Rate the program')
        self.assertEqual(q2.question_type.name, 'Rating')
        self.assertEqual(q2.param_values, ['1', '5'])
        self.assertEqual(q2.seq, 2)
    
    def test_import_questions_with_invalid_csv(self):
        """Test that invalid CSV shows validation errors."""
        csv_content = """question_name,question_type,param_values,per_class,sequence
Question 1,InvalidType,,false,1"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'
        
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request(
            method='POST',
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        
        response = self.admin.import_questions(request, queryset)
        
        # Should render form with errors
        self.assertEqual(response.status_code, 200)
        
        # No questions should be created
        self.assertEqual(Question.objects.filter(survey=self.survey).count(), 0)
    
    def test_import_questions_with_duplicates(self):
        """Test that duplicates trigger resolution form."""
        # Create an existing question
        Question.objects.create(
            survey=self.survey,
            name='Existing Question',
            question_type=self.qt_yesno,
            seq=1,
            per_class=False
        )
        
        # Try to import a duplicate
        csv_content = """question_name,question_type,param_values,per_class,sequence
Existing Question,Yes/No,,false,2"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'
        
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request(
            method='POST',
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        
        response = self.admin.import_questions(request, queryset)
        
        # Should render duplicate resolution form
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Resolve Duplicate Questions', response.content)

    def test_batch_import_results_reporting(self):
        """Test that batch import results are reported separately for each survey."""
        # Create a second survey
        survey2 = Survey.objects.create(
            name='Test Survey 2',
            program=self.program,
            category='learn'
        )
        
        # Create valid CSV content
        csv_content = """question_name,question_type,param_values,per_class,sequence
Question 1,Yes/No,,false,1
Question 2,Multiple Choice,Option A|Option B|Option C,false,2"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'
        
        # Import into both surveys
        queryset = Survey.objects.filter(id__in=[self.survey.id, survey2.id])
        request = self._create_request(
            method='POST',
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        
        response = self.admin.import_questions(request, queryset)
        
        # Should redirect after successful import
        self.assertEqual(response.status_code, 302)
        
        # Check that messages were created
        messages_list = list(messages.get_messages(request))
        
        # Should have summary message
        summary_messages = [m for m in messages_list if 'Batch import complete' in str(m)]
        self.assertEqual(len(summary_messages), 1)
        self.assertIn('2 survey(s) succeeded', str(summary_messages[0]))
        self.assertIn('0 survey(s) failed', str(summary_messages[0]))
        
        # Should have per-survey success messages
        survey_messages = [m for m in messages_list if '✓' in str(m)]
        self.assertEqual(len(survey_messages), 2)
        
        # Verify both surveys have the questions
        self.assertEqual(self.survey.question_set.count(), 2)
        self.assertEqual(survey2.question_set.count(), 2)
        
        # Verify message content includes counts
        for msg in survey_messages:
            self.assertIn('2 created', str(msg))

    def test_batch_import_with_failures(self):
        """Test that batch import continues on failure and reports errors separately."""
        # Create a second survey
        survey2 = Survey.objects.create(
            name='Test Survey 2',
            program=self.program,
            category='learn'
        )
        
        # Create a third survey
        survey3 = Survey.objects.create(
            name='Test Survey 3',
            program=self.program,
            category='learn'
        )
        
        # Add an existing question to survey2 to create a duplicate scenario
        Question.objects.create(
            survey=survey2,
            name='Question 1',
            question_type=self.qt_yesno,
            seq=1,
            per_class=False
        )
        
        # Create valid CSV content
        csv_content = """question_name,question_type,param_values,per_class,sequence
Question 1,Yes/No,,false,1
Question 2,Multiple Choice,Option A|Option B|Option C,false,2"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test.csv'
        
        # Import into all three surveys
        queryset = Survey.objects.filter(id__in=[self.survey.id, survey2.id, survey3.id])
        request = self._create_request(
            method='POST',
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        
        response = self.admin.import_questions(request, queryset)
        
        # Should redirect after import
        self.assertEqual(response.status_code, 302)
        
        # Check messages
        messages_list = list(messages.get_messages(request))
        
        # Should have summary message
        summary_messages = [m for m in messages_list if 'Batch import complete' in str(m)]
        self.assertEqual(len(summary_messages), 1)
        self.assertIn('3 survey(s) succeeded', str(summary_messages[0]))
        
        # Should have per-survey messages
        success_messages = [m for m in messages_list if '✓' in str(m)]
        self.assertEqual(len(success_messages), 3)
        
        # Verify survey1 has 2 questions
        self.assertEqual(self.survey.question_set.count(), 2)
        
        # Verify survey2 has 2 questions (1 existing + 1 new, 1 skipped)
        self.assertEqual(survey2.question_set.count(), 2)
        
        # Verify survey3 has 2 questions
        self.assertEqual(survey3.question_set.count(), 2)


class SurveyAdminExportTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        
        # Create test user
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password'
        )
        
        # Create test program and survey
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        
        # Create question types
        self.qt_yesno = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.qt_rating = QuestionType.objects.create(
            name='Rating',
            _param_names='min|max',
            is_numeric=True,
            is_countable=True,
        )
        
        # Setup admin
        self.site = AdminSite()
        self.admin = SurveyAdmin(Survey, self.site)
        self.factory = RequestFactory()
    
    def _create_request(self, method='GET'):
        """Helper to create a request with session and messages."""
        if method == 'GET':
            request = self.factory.get('/admin/survey/survey/')
        else:
            request = self.factory.post('/admin/survey/survey/')
        
        request.user = self.user
        
        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add messages
        setattr(request, '_messages', FallbackStorage(request))
        
        return request
    
    def test_export_questions_action_exists(self):
        """Test that export_questions action is registered."""
        self.assertIn('export_questions', self.admin.actions)
    
    def test_export_questions_requires_single_survey(self):
        """Test that export action requires exactly one survey."""
        # Create another survey
        survey2 = Survey.objects.create(
            name='Test Survey 2',
            program=self.program,
            category='teach',
        )
        
        # Try with multiple surveys
        queryset = Survey.objects.filter(id__in=[self.survey.id, survey2.id])
        request = self._create_request()
        
        response = self.admin.export_questions(request, queryset)
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
    
    def test_export_questions_returns_csv(self):
        """Test that export action returns CSV file."""
        # Create test questions
        Question.objects.create(
            survey=self.survey,
            name='Did you enjoy the program?',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Rate the program',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=False,
            seq=2
        )
        
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request()
        
        response = self.admin.export_questions(request, queryset)
        
        # Should return CSV response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Test Survey_questions.csv', response['Content-Disposition'])
        
        # Verify CSV content
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have header + 2 data rows
        self.assertEqual(len(lines), 3)
        
        # Verify header
        self.assertIn('question_name', lines[0])
        self.assertIn('question_type', lines[0])
        self.assertIn('param_values', lines[0])
        self.assertIn('per_class', lines[0])
        self.assertIn('sequence', lines[0])
        
        # Verify first question
        self.assertIn('Did you enjoy the program?', lines[1])
        self.assertIn('Yes/No', lines[1])
        
        # Verify second question
        self.assertIn('Rate the program', lines[2])
        self.assertIn('Rating', lines[2])
        self.assertIn('1|5', lines[2])
    
    def test_export_questions_empty_survey(self):
        """Test exporting from survey with no questions."""
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request()
        
        response = self.admin.export_questions(request, queryset)
        
        # Should return CSV with header only
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Should have only header row
        self.assertEqual(len(lines), 1)
        self.assertIn('question_name', lines[0])
    
    def test_export_questions_ordered_by_sequence(self):
        """Test that exported questions are ordered by sequence."""
        # Create questions in non-sequential order
        Question.objects.create(
            survey=self.survey,
            name='Question 3',
            question_type=self.qt_yesno,
            seq=3
        )
        Question.objects.create(
            survey=self.survey,
            name='Question 1',
            question_type=self.qt_yesno,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Question 2',
            question_type=self.qt_yesno,
            seq=2
        )
        
        queryset = Survey.objects.filter(id=self.survey.id)
        request = self._create_request()
        
        response = self.admin.export_questions(request, queryset)
        
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        # Verify order (skip header)
        self.assertIn('Question 1', lines[1])
        self.assertIn('Question 2', lines[2])
        self.assertIn('Question 3', lines[3])

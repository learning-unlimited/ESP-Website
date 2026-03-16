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

"""
Tests for esp.survey.importers
Source: esp/esp/survey/importers.py

Tests CSVQuestionImporter and QuestionValidator classes.
"""
import io

from django.contrib.auth.models import Group

from esp.program.models import Program
from esp.survey.models import Survey, QuestionType, Question
from esp.survey.importers import (
    CSVQuestionImporter,
    QuestionValidator,
    QuestionData,
    ValidationError,
)
from esp.tests.util import CacheFlushTestCase as TestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class CSVQuestionImporterTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        # Create a question type for testing
        self.qt = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.qt_with_params = QuestionType.objects.create(
            name='Rating',
            _param_names='min|max',
            is_numeric=True,
            is_countable=True,
        )

    def test_parse_valid_csv(self):
        """Test parsing a valid CSV file."""
        csv_data = """question_name,question_type,param_values,per_class,sequence
Do you like this?,Yes/No,,false,1
Rate this class,Rating,1|5,true,2"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        questions = importer.parse_questions()
        
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].question_name, 'Do you like this?')
        self.assertEqual(questions[0].question_type_name, 'Yes/No')
        self.assertEqual(questions[0].per_class, False)
        self.assertEqual(questions[0].sequence, 1)
        
        self.assertEqual(questions[1].question_name, 'Rate this class')
        self.assertEqual(questions[1].question_type_name, 'Rating')
        self.assertEqual(questions[1].param_values, ['1', '5'])
        self.assertEqual(questions[1].per_class, True)
        self.assertEqual(questions[1].sequence, 2)

    def test_parse_csv_with_optional_columns_missing(self):
        """Test parsing CSV with only required columns."""
        csv_data = """question_name,question_type
Simple question,Yes/No"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        questions = importer.parse_questions()
        
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_name, 'Simple question')
        self.assertEqual(questions[0].param_values, [])
        self.assertEqual(questions[0].per_class, False)
        self.assertIsNone(questions[0].sequence)

    def test_parse_csv_missing_required_column(self):
        """Test that missing required columns raise an error."""
        csv_data = """question_name
Missing type column"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        self.assertIn('Missing required columns', str(context.exception))
        self.assertIn('question_type', str(context.exception))

    def test_parse_boolean_values(self):
        """Test parsing various boolean formats."""
        csv_data = """question_name,question_type,per_class
Q1,Yes/No,true
Q2,Yes/No,false
Q3,Yes/No,1
Q4,Yes/No,0
Q5,Yes/No,yes
Q6,Yes/No,no
Q7,Yes/No,"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        questions = importer.parse_questions()
        
        self.assertEqual(questions[0].per_class, True)
        self.assertEqual(questions[1].per_class, False)
        self.assertEqual(questions[2].per_class, True)
        self.assertEqual(questions[3].per_class, False)
        self.assertEqual(questions[4].per_class, True)
        self.assertEqual(questions[5].per_class, False)
        self.assertEqual(questions[6].per_class, False)

    def test_validate_valid_csv(self):
        """Test validation of a valid CSV."""
        csv_data = """question_name,question_type
Valid question,Yes/No"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.validate()
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)

    def test_validate_invalid_question_type(self):
        """Test validation catches invalid question type."""
        csv_data = """question_name,question_type
Question with bad type,NonExistentType"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.validate()
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIn('does not exist', result['errors'][0].message)


class QuestionValidatorTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        # Create question types for testing
        self.qt_no_params = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.qt_with_params = QuestionType.objects.create(
            name='Rating',
            _param_names='min|max',
            is_numeric=True,
            is_countable=True,
        )

    def test_validate_valid_row(self):
        """Test validation of a valid row."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'Valid question',
            'question_type': 'Yes/No',
            'param_values': [],
            'per_class': False,
            'sequence': 1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertEqual(len(errors), 0)

    def test_validate_question_name_too_long(self):
        """Test validation catches question name exceeding 255 characters."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'x' * 256,
            'question_type': 'Yes/No',
            'param_values': [],
            'per_class': False,
            'sequence': 1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('exceeds 255 characters', errors[0].message)

    def test_validate_question_name_empty(self):
        """Test validation catches empty question name."""
        validator = QuestionValidator()
        row_data = {
            'question_name': '',
            'question_type': 'Yes/No',
            'param_values': [],
            'per_class': False,
            'sequence': 1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('required', errors[0].message)

    def test_validate_question_type_not_exists(self):
        """Test validation catches non-existent question type."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'Test question',
            'question_type': 'NonExistentType',
            'param_values': [],
            'per_class': False,
            'sequence': 1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('does not exist', errors[0].message)

    def test_validate_insufficient_params(self):
        """Test validation catches insufficient param_values."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'Rating question',
            'question_type': 'Rating',
            'param_values': ['1'],  # Needs 2 params (min and max)
            'per_class': False,
            'sequence': 1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('requires 2 parameters', errors[0].message)

    def test_validate_invalid_per_class(self):
        """Test validation catches invalid per_class values."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'Test question',
            'question_type': 'Yes/No',
            'param_values': [],
            'per_class': 'invalid',
            'sequence': 1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('per_class must be', errors[0].message)

    def test_validate_invalid_sequence(self):
        """Test validation catches invalid sequence values."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'Test question',
            'question_type': 'Yes/No',
            'param_values': [],
            'per_class': False,
            'sequence': 'not_a_number'
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('positive integer', errors[0].message)

    def test_validate_negative_sequence(self):
        """Test validation catches negative sequence values."""
        validator = QuestionValidator()
        row_data = {
            'question_name': 'Test question',
            'question_type': 'Yes/No',
            'param_values': [],
            'per_class': False,
            'sequence': -1
        }
        
        errors = validator.validate_row(2, row_data)
        self.assertGreater(len(errors), 0)
        self.assertIn('positive integer', errors[0].message)


class DuplicateDetectionTest(TestCase):
    """Tests for duplicate detection functionality."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
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
        # Create an existing question
        self.existing_question = Question.objects.create(
            survey=self.survey,
            name='Existing Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )

    def test_check_duplicates_detects_duplicate_by_name_and_type(self):
        """Test that duplicates are detected when both name and type match."""
        validator = QuestionValidator()
        questions = [
            QuestionData(
                row_number=2,
                question_name='Existing Question',
                question_type_name='Yes/No',
                param_values=[],
                per_class=False,
                sequence=None
            )
        ]
        
        duplicates = validator.check_duplicates(questions, self.survey)
        
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0].existing_question.id, self.existing_question.id)
        self.assertEqual(duplicates[0].question_data.question_name, 'Existing Question')

    def test_check_duplicates_no_false_positive_name_only(self):
        """Test that no duplicate is detected when only name matches."""
        validator = QuestionValidator()
        questions = [
            QuestionData(
                row_number=2,
                question_name='Existing Question',
                question_type_name='Rating',  # Different type
                param_values=['1', '5'],
                per_class=False,
                sequence=None
            )
        ]
        
        duplicates = validator.check_duplicates(questions, self.survey)
        
        self.assertEqual(len(duplicates), 0)

    def test_check_duplicates_no_false_positive_type_only(self):
        """Test that no duplicate is detected when only type matches."""
        validator = QuestionValidator()
        questions = [
            QuestionData(
                row_number=2,
                question_name='Different Question',  # Different name
                question_type_name='Yes/No',
                param_values=[],
                per_class=False,
                sequence=None
            )
        ]
        
        duplicates = validator.check_duplicates(questions, self.survey)
        
        self.assertEqual(len(duplicates), 0)

    def test_check_duplicates_multiple_duplicates(self):
        """Test detection of multiple duplicates in single import."""
        # Create another existing question
        Question.objects.create(
            survey=self.survey,
            name='Another Question',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=True,
            seq=2
        )
        
        validator = QuestionValidator()
        questions = [
            QuestionData(
                row_number=2,
                question_name='Existing Question',
                question_type_name='Yes/No',
                param_values=[],
                per_class=False,
                sequence=None
            ),
            QuestionData(
                row_number=3,
                question_name='Another Question',
                question_type_name='Rating',
                param_values=['1', '10'],
                per_class=False,
                sequence=None
            )
        ]
        
        duplicates = validator.check_duplicates(questions, self.survey)
        
        self.assertEqual(len(duplicates), 2)


class DuplicateResolutionTest(TestCase):
    """Tests for duplicate resolution strategies."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
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

    def test_skip_strategy_prevents_creation(self):
        """Test that skip strategy does not create duplicate question."""
        # Create existing question
        existing = Question.objects.create(
            survey=self.survey,
            name='Duplicate Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        
        csv_data = """question_name,question_type
Duplicate Question,Yes/No"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Use skip strategy
        duplicate_strategy = {
            'Duplicate Question|Yes/No': 'skip'
        }
        
        result = importer.import_questions(duplicate_strategy)
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.updated_count, 0)
        
        # Verify existing question unchanged
        existing.refresh_from_db()
        self.assertEqual(existing.name, 'Duplicate Question')
        self.assertEqual(existing.seq, 1)
        
        # Verify no new question created
        self.assertEqual(Question.objects.filter(survey=self.survey).count(), 1)

    def test_replace_strategy_updates_existing(self):
        """Test that replace strategy updates existing question."""
        # Create existing question
        existing = Question.objects.create(
            survey=self.survey,
            name='Duplicate Question',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=False,
            seq=1
        )
        
        csv_data = """question_name,question_type,param_values,sequence
Duplicate Question,Rating,1|10,5"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Use replace strategy
        duplicate_strategy = {
            'Duplicate Question|Rating': 'replace'
        }
        
        result = importer.import_questions(duplicate_strategy)
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.updated_count, 1)
        
        # Verify existing question updated
        existing.refresh_from_db()
        self.assertEqual(existing._param_values, '1|10')
        self.assertEqual(existing.seq, 5)
        
        # Verify no new question created
        self.assertEqual(Question.objects.filter(survey=self.survey).count(), 1)

    def test_rename_strategy_creates_new_question(self):
        """Test that rename strategy creates new question with suffix."""
        # Create existing question
        existing = Question.objects.create(
            survey=self.survey,
            name='Duplicate Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        
        csv_data = """question_name,question_type,sequence
Duplicate Question,Yes/No,2"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Use rename strategy
        duplicate_strategy = {
            'Duplicate Question|Yes/No': 'rename'
        }
        
        result = importer.import_questions(duplicate_strategy)
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.updated_count, 0)
        
        # Verify existing question unchanged
        existing.refresh_from_db()
        self.assertEqual(existing.name, 'Duplicate Question')
        self.assertEqual(existing.seq, 1)
        
        # Verify new question created with suffix
        self.assertEqual(Question.objects.filter(survey=self.survey).count(), 2)
        new_question = Question.objects.get(survey=self.survey, seq=2)
        self.assertEqual(new_question.name, 'Duplicate Question_1')
        self.assertEqual(new_question.question_type, self.qt_yesno)

    def test_rename_strategy_increments_suffix(self):
        """Test that rename strategy increments suffix for multiple duplicates."""
        # Create existing questions
        Question.objects.create(
            survey=self.survey,
            name='Duplicate Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Duplicate Question_1',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=2
        )
        
        csv_data = """question_name,question_type
Duplicate Question,Yes/No"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Use rename strategy
        duplicate_strategy = {
            'Duplicate Question|Yes/No': 'rename'
        }
        
        result = importer.import_questions(duplicate_strategy)
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 1)
        
        # Verify new question created with suffix _2
        new_question = Question.objects.get(survey=self.survey, name='Duplicate Question_2')
        self.assertIsNotNone(new_question)

    def test_import_without_duplicates(self):
        """Test that import works normally when no duplicates exist."""
        csv_data = """question_name,question_type,sequence
New Question,Yes/No,1"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.updated_count, 0)
        
        # Verify question created
        question = Question.objects.get(survey=self.survey, name='New Question')
        self.assertEqual(question.question_type, self.qt_yesno)
        self.assertEqual(question.seq, 1)

    def test_mixed_strategies_in_single_import(self):
        """Test using different strategies for different duplicates."""
        # Create existing questions
        Question.objects.create(
            survey=self.survey,
            name='Skip This',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Replace This',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=False,
            seq=2
        )
        Question.objects.create(
            survey=self.survey,
            name='Rename This',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=True,
            seq=3
        )
        
        csv_data = """question_name,question_type,param_values,sequence
Skip This,Yes/No,,10
Replace This,Rating,1|10,20
Rename This,Yes/No,,30
New Question,Yes/No,,40"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Use different strategies
        duplicate_strategy = {
            'Skip This|Yes/No': 'skip',
            'Replace This|Rating': 'replace',
            'Rename This|Yes/No': 'rename'
        }
        
        result = importer.import_questions(duplicate_strategy)
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 2)  # Rename This_1 and New Question
        self.assertEqual(result.skipped_count, 1)  # Skip This
        self.assertEqual(result.updated_count, 1)  # Replace This
        
        # Verify results
        self.assertEqual(Question.objects.filter(survey=self.survey).count(), 5)
        
        # Skip This should be unchanged
        skip_q = Question.objects.get(survey=self.survey, name='Skip This')
        self.assertEqual(skip_q.seq, 1)
        
        # Replace This should be updated
        replace_q = Question.objects.get(survey=self.survey, name='Replace This')
        self.assertEqual(replace_q._param_values, '1|10')
        self.assertEqual(replace_q.seq, 20)
        
        # Rename This should be unchanged, new one created
        rename_q = Question.objects.get(survey=self.survey, name='Rename This')
        self.assertEqual(rename_q.seq, 3)
        new_rename_q = Question.objects.get(survey=self.survey, name='Rename This_1')
        self.assertEqual(new_rename_q.seq, 30)
        
        # New Question should be created
        new_q = Question.objects.get(survey=self.survey, name='New Question')
        self.assertEqual(new_q.seq, 40)

    def test_default_skip_strategy_when_not_specified(self):
        """Test that skip is the default strategy when none is specified."""
        # Create existing question
        Question.objects.create(
            survey=self.survey,
            name='Duplicate Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        
        csv_data = """question_name,question_type
Duplicate Question,Yes/No"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Don't specify strategy for this duplicate
        result = importer.import_questions({})
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.updated_count, 0)


class TemplateManagerTest(TestCase):
    """Tests for TemplateManager class."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        # Create question types that match the templates
        QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        QuestionType.objects.create(
            name='Rating',
            _param_names='min|max',
            is_numeric=True,
            is_countable=True,
        )
        QuestionType.objects.create(
            name='Free Response',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )

    def test_list_templates_returns_all_templates(self):
        """Test that list_templates returns all CSV files in template directory."""
        from esp.survey.importers import TemplateManager
        
        templates = TemplateManager.list_templates()
        
        # Should have at least the two templates we created
        self.assertGreaterEqual(len(templates), 2)
        self.assertIn('student_program_feedback.csv', templates)
        self.assertIn('teacher_program_feedback.csv', templates)

    def test_list_templates_filtered_by_category(self):
        """Test that list_templates can filter by category."""
        from esp.survey.importers import TemplateManager
        
        student_templates = TemplateManager.list_templates(category='student')
        teacher_templates = TemplateManager.list_templates(category='teacher')
        
        # Should have at least one of each
        self.assertGreaterEqual(len(student_templates), 1)
        self.assertGreaterEqual(len(teacher_templates), 1)
        
        # Student templates should start with 'student_'
        for template in student_templates:
            self.assertTrue(template.startswith('student_'))
        
        # Teacher templates should start with 'teacher_'
        for template in teacher_templates:
            self.assertTrue(template.startswith('teacher_'))

    def test_load_template_returns_importer(self):
        """Test that load_template returns a CSVQuestionImporter instance."""
        from esp.survey.importers import TemplateManager
        
        importer = TemplateManager.load_template('student_program_feedback.csv', self.survey)
        
        self.assertIsInstance(importer, CSVQuestionImporter)
        self.assertEqual(importer.target_survey, self.survey)

    def test_load_template_without_csv_extension(self):
        """Test that load_template works without .csv extension."""
        from esp.survey.importers import TemplateManager
        
        importer = TemplateManager.load_template('student_program_feedback', self.survey)
        
        self.assertIsInstance(importer, CSVQuestionImporter)

    def test_load_template_nonexistent_raises_error(self):
        """Test that loading a non-existent template raises FileNotFoundError."""
        from esp.survey.importers import TemplateManager
        
        with self.assertRaises(FileNotFoundError):
            TemplateManager.load_template('nonexistent_template.csv', self.survey)

    def test_load_template_can_parse_questions(self):
        """Test that loaded template can parse questions."""
        from esp.survey.importers import TemplateManager
        
        importer = TemplateManager.load_template('student_program_feedback.csv', self.survey)
        questions = importer.parse_questions()
        
        # Student template should have 8 questions
        self.assertEqual(len(questions), 8)
        
        # Verify first question
        self.assertEqual(questions[0].question_name, 'Overall Program Rating')
        self.assertEqual(questions[0].question_type_name, 'Rating')
        self.assertEqual(questions[0].param_values, ['1', '5'])
        self.assertEqual(questions[0].per_class, False)
        self.assertEqual(questions[0].sequence, 1)

    def test_load_template_can_import_questions(self):
        """Test that loaded template can import questions into survey."""
        from esp.survey.importers import TemplateManager
        
        importer = TemplateManager.load_template('teacher_program_feedback.csv', self.survey)
        result = importer.import_questions()
        
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 8)  # Teacher template has 8 questions
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.updated_count, 0)
        
        # Verify questions were created
        questions = Question.objects.filter(survey=self.survey).order_by('seq')
        self.assertEqual(questions.count(), 8)
        
        # Verify first question
        first_q = questions.first()
        self.assertEqual(first_q.name, 'Overall Teaching Experience Rating')
        self.assertEqual(first_q.question_type.name, 'Rating')


class ExportQuestionsTest(TestCase):
    """Tests for CSV export functionality."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
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

    def test_export_empty_survey(self):
        """Test exporting a survey with no questions."""
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        # Should have header row only
        lines = csv_data.strip().split('\n')
        self.assertEqual(len(lines), 1)
        self.assertIn('question_name', lines[0])
        self.assertIn('question_type', lines[0])

    def test_export_single_question(self):
        """Test exporting a survey with one question."""
        Question.objects.create(
            survey=self.survey,
            name='Test Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        # Should have header + 1 data row
        lines = csv_data.strip().split('\n')
        self.assertEqual(len(lines), 2)
        
        # Verify data row contains question info
        self.assertIn('Test Question', csv_data)
        self.assertIn('Yes/No', csv_data)
        self.assertIn('false', csv_data)

    def test_export_multiple_questions_ordered_by_sequence(self):
        """Test that export orders questions by sequence."""
        Question.objects.create(
            survey=self.survey,
            name='Question 3',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=3
        )
        Question.objects.create(
            survey=self.survey,
            name='Question 1',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Question 2',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=True,
            seq=2
        )
        
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        # Parse CSV to verify order
        lines = csv_data.strip().split('\n')
        self.assertEqual(len(lines), 4)  # Header + 3 questions
        
        # Verify order by checking which question appears first
        self.assertIn('Question 1', lines[1])
        self.assertIn('Question 2', lines[2])
        self.assertIn('Question 3', lines[3])

    def test_export_formats_param_values_as_pipe_delimited(self):
        """Test that param_values are formatted as pipe-delimited string."""
        Question.objects.create(
            survey=self.survey,
            name='Rating Question',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=False,
            seq=1
        )
        
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        # Verify pipe-delimited format
        self.assertIn('1|5', csv_data)

    def test_export_formats_per_class_as_true_false(self):
        """Test that per_class is formatted as true/false."""
        Question.objects.create(
            survey=self.survey,
            name='Per Class Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=True,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Not Per Class Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=2
        )
        
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        lines = csv_data.strip().split('\n')
        # Check that 'true' and 'false' appear in the data
        self.assertIn('true', lines[1])
        self.assertIn('false', lines[2])

    def test_export_includes_all_required_columns(self):
        """Test that export includes all required columns."""
        Question.objects.create(
            survey=self.survey,
            name='Test Question',
            question_type=self.qt_rating,
            _param_values='1|10',
            per_class=True,
            seq=5
        )
        
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        # Parse CSV and verify columns
        import csv as csv_module
        reader = csv_module.DictReader(io.StringIO(csv_data))
        
        # Check fieldnames
        self.assertIn('question_name', reader.fieldnames)
        self.assertIn('question_type', reader.fieldnames)
        self.assertIn('param_values', reader.fieldnames)
        self.assertIn('per_class', reader.fieldnames)
        self.assertIn('sequence', reader.fieldnames)
        
        # Check data row
        row = next(reader)
        self.assertEqual(row['question_name'], 'Test Question')
        self.assertEqual(row['question_type'], 'Rating')
        self.assertEqual(row['param_values'], '1|10')
        self.assertEqual(row['per_class'], 'true')
        self.assertEqual(row['sequence'], '5')

    def test_export_import_round_trip(self):
        """Test that exporting and importing preserves data."""
        # Create questions
        Question.objects.create(
            survey=self.survey,
            name='Question 1',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        Question.objects.create(
            survey=self.survey,
            name='Question 2',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=True,
            seq=2
        )
        
        # Export
        csv_data = CSVQuestionImporter.export_questions(self.survey)
        
        # Create new survey and import
        new_survey = Survey.objects.create(
            name='New Survey',
            program=self.program,
            category='learn',
        )
        importer = CSVQuestionImporter(csv_data, new_survey)
        result = importer.import_questions()
        
        # Verify import succeeded
        self.assertTrue(result.success)
        self.assertEqual(result.created_count, 2)
        
        # Verify questions match
        original_questions = Question.objects.filter(survey=self.survey).order_by('seq')
        imported_questions = Question.objects.filter(survey=new_survey).order_by('seq')
        
        self.assertEqual(original_questions.count(), imported_questions.count())
        
        for orig, imported in zip(original_questions, imported_questions):
            self.assertEqual(orig.name, imported.name)
            self.assertEqual(orig.question_type.name, imported.question_type.name)
            self.assertEqual(orig.param_values, imported.param_values)
            self.assertEqual(orig.per_class, imported.per_class)
            self.assertEqual(orig.seq, imported.seq)


class QuestionImportFormTest(TestCase):
    """Tests for QuestionImportForm."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        # Create question types that match the templates
        QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )

    def test_form_has_required_fields(self):
        """Test that form has all required fields."""
        from esp.survey.forms import QuestionImportForm
        
        form = QuestionImportForm()
        
        self.assertIn('import_source', form.fields)
        self.assertIn('csv_file', form.fields)
        self.assertIn('template', form.fields)

    def test_import_source_choices(self):
        """Test that import_source has correct choices."""
        from esp.survey.forms import QuestionImportForm
        
        form = QuestionImportForm()
        
        choices = form.fields['import_source'].choices
        self.assertEqual(len(choices), 2)
        self.assertIn(('upload', 'Upload CSV'), choices)
        self.assertIn(('template', 'Use Template'), choices)

    def test_template_field_populated_from_template_manager(self):
        """Test that template field is populated with available templates."""
        from esp.survey.forms import QuestionImportForm
        from esp.survey.importers import TemplateManager
        
        form = QuestionImportForm()
        
        # Get template choices (excluding the empty choice)
        template_choices = [choice[0] for choice in form.fields['template'].choices if choice[0]]
        
        # Get templates from TemplateManager
        available_templates = TemplateManager.list_templates()
        
        # Verify all available templates are in the form choices
        for template in available_templates:
            self.assertIn(template, template_choices)

    def test_csv_file_and_template_are_optional(self):
        """Test that csv_file and template fields are not required."""
        from esp.survey.forms import QuestionImportForm
        
        form = QuestionImportForm()
        
        self.assertFalse(form.fields['csv_file'].required)
        self.assertFalse(form.fields['template'].required)

    def test_clean_validates_upload_source_requires_csv_file(self):
        """Test that upload source requires csv_file."""
        from esp.survey.forms import QuestionImportForm
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Test without csv_file
        form = QuestionImportForm(data={'import_source': 'upload'})
        self.assertFalse(form.is_valid())
        self.assertIn('Please upload a CSV file', str(form.errors))
        
        # Test with csv_file
        csv_content = b'question_name,question_type\nTest,Yes/No'
        csv_file = SimpleUploadedFile('test.csv', csv_content, content_type='text/csv')
        form = QuestionImportForm(
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        self.assertTrue(form.is_valid())

    def test_clean_validates_template_source_requires_template(self):
        """Test that template source requires template selection."""
        from esp.survey.forms import QuestionImportForm
        
        # Test without template
        form = QuestionImportForm(data={'import_source': 'template'})
        self.assertFalse(form.is_valid())
        self.assertIn('Please select a template', str(form.errors))
        
        # Test with template
        form = QuestionImportForm(data={
            'import_source': 'template',
            'template': 'student_program_feedback.csv'
        })
        self.assertTrue(form.is_valid())

    def test_form_valid_with_upload_source_and_csv_file(self):
        """Test that form is valid with upload source and csv_file."""
        from esp.survey.forms import QuestionImportForm
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        csv_content = b'question_name,question_type\nTest Question,Yes/No'
        csv_file = SimpleUploadedFile('test.csv', csv_content, content_type='text/csv')
        
        form = QuestionImportForm(
            data={'import_source': 'upload'},
            files={'csv_file': csv_file}
        )
        
        self.assertTrue(form.is_valid())

    def test_form_valid_with_template_source_and_template(self):
        """Test that form is valid with template source and template selection."""
        from esp.survey.forms import QuestionImportForm
        
        form = QuestionImportForm(data={
            'import_source': 'template',
            'template': 'student_program_feedback.csv'
        })
        
        self.assertTrue(form.is_valid())


class DuplicateResolutionFormTest(TestCase):
    """Tests for DuplicateResolutionForm."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
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

    def test_form_creates_field_for_each_duplicate(self):
        """Test that form creates a field for each duplicate."""
        from esp.survey.forms import DuplicateResolutionForm
        from esp.survey.importers import Duplicate, QuestionData
        
        # Create existing questions
        existing_q1 = Question.objects.create(
            survey=self.survey,
            name='Question 1',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        existing_q2 = Question.objects.create(
            survey=self.survey,
            name='Question 2',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=True,
            seq=2
        )
        
        # Create duplicate objects
        duplicates = [
            Duplicate(
                question_data=QuestionData(
                    row_number=2,
                    question_name='Question 1',
                    question_type_name='Yes/No',
                    param_values=[],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q1
            ),
            Duplicate(
                question_data=QuestionData(
                    row_number=3,
                    question_name='Question 2',
                    question_type_name='Rating',
                    param_values=['1', '10'],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q2
            )
        ]
        
        form = DuplicateResolutionForm(duplicates)
        
        # Verify fields were created
        self.assertIn(f'duplicate_{existing_q1.id}', form.fields)
        self.assertIn(f'duplicate_{existing_q2.id}', form.fields)
        self.assertEqual(len(form.fields), 2)

    def test_field_has_correct_choices(self):
        """Test that each field has skip/replace/rename choices."""
        from esp.survey.forms import DuplicateResolutionForm
        from esp.survey.importers import Duplicate, QuestionData
        
        existing_q = Question.objects.create(
            survey=self.survey,
            name='Test Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        
        duplicates = [
            Duplicate(
                question_data=QuestionData(
                    row_number=2,
                    question_name='Test Question',
                    question_type_name='Yes/No',
                    param_values=[],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q
            )
        ]
        
        form = DuplicateResolutionForm(duplicates)
        
        field_name = f'duplicate_{existing_q.id}'
        field = form.fields[field_name]
        
        # Verify choices
        choices = [choice[0] for choice in field.choices]
        self.assertIn('skip', choices)
        self.assertIn('replace', choices)
        self.assertIn('rename', choices)
        self.assertEqual(len(choices), 3)

    def test_field_label_shows_question_name_and_type(self):
        """Test that field label includes question name and type."""
        from esp.survey.forms import DuplicateResolutionForm
        from esp.survey.importers import Duplicate, QuestionData
        
        existing_q = Question.objects.create(
            survey=self.survey,
            name='My Test Question',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=False,
            seq=1
        )
        
        duplicates = [
            Duplicate(
                question_data=QuestionData(
                    row_number=2,
                    question_name='My Test Question',
                    question_type_name='Rating',
                    param_values=['1', '10'],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q
            )
        ]
        
        form = DuplicateResolutionForm(duplicates)
        
        field_name = f'duplicate_{existing_q.id}'
        field = form.fields[field_name]
        
        # Verify label contains question name and type
        self.assertIn('My Test Question', field.label)
        self.assertIn('Rating', field.label)

    def test_field_default_value_is_skip(self):
        """Test that default value for each field is 'skip'."""
        from esp.survey.forms import DuplicateResolutionForm
        from esp.survey.importers import Duplicate, QuestionData
        
        existing_q = Question.objects.create(
            survey=self.survey,
            name='Test Question',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        
        duplicates = [
            Duplicate(
                question_data=QuestionData(
                    row_number=2,
                    question_name='Test Question',
                    question_type_name='Yes/No',
                    param_values=[],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q
            )
        ]
        
        form = DuplicateResolutionForm(duplicates)
        
        field_name = f'duplicate_{existing_q.id}'
        field = form.fields[field_name]
        
        self.assertEqual(field.initial, 'skip')

    def test_get_strategies_returns_correct_mapping(self):
        """Test that get_strategies returns correct strategy mapping."""
        from esp.survey.forms import DuplicateResolutionForm
        from esp.survey.importers import Duplicate, QuestionData
        
        existing_q1 = Question.objects.create(
            survey=self.survey,
            name='Question 1',
            question_type=self.qt_yesno,
            _param_values='',
            per_class=False,
            seq=1
        )
        existing_q2 = Question.objects.create(
            survey=self.survey,
            name='Question 2',
            question_type=self.qt_rating,
            _param_values='1|5',
            per_class=True,
            seq=2
        )
        
        duplicates = [
            Duplicate(
                question_data=QuestionData(
                    row_number=2,
                    question_name='Question 1',
                    question_type_name='Yes/No',
                    param_values=[],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q1
            ),
            Duplicate(
                question_data=QuestionData(
                    row_number=3,
                    question_name='Question 2',
                    question_type_name='Rating',
                    param_values=['1', '10'],
                    per_class=False,
                    sequence=None
                ),
                existing_question=existing_q2
            )
        ]
        
        # Create form with data
        form_data = {
            f'duplicate_{existing_q1.id}': 'replace',
            f'duplicate_{existing_q2.id}': 'rename'
        }
        form = DuplicateResolutionForm(duplicates, data=form_data)
        
        self.assertTrue(form.is_valid())
        
        strategies = form.get_strategies(duplicates)
        
        # Verify strategy mapping
        self.assertEqual(strategies['Question 1|Yes/No'], 'replace')
        self.assertEqual(strategies['Question 2|Rating'], 'rename')

    def test_form_with_no_duplicates(self):
        """Test that form works with empty duplicates list."""
        from esp.survey.forms import DuplicateResolutionForm
        
        form = DuplicateResolutionForm([])
        
        # Should have no fields
        self.assertEqual(len(form.fields), 0)
        self.assertTrue(form.is_valid())



class ImportLoggerTest(TestCase):
    """Tests for ImportLogger audit logging functionality."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        
        # Create a test user
        from esp.users.models import ESPUser
        self.user = ESPUser.objects.create_user(
            username='testadmin',
            email='testadmin@example.com',
            password='testpass'
        )

    def test_log_start_creates_log_entry(self):
        """Test that log_start creates a log entry with correct data."""
        from esp.survey.importers import ImportLogger
        import logging
        import json
        
        # Capture log output
        with self.assertLogs('esp.survey.import', level='INFO') as cm:
            logger = ImportLogger()
            logger.log_start(self.user, [self.survey], 'CSV upload')
        
        # Verify log was created
        self.assertEqual(len(cm.output), 1)
        
        # Parse the JSON log data
        log_message = cm.output[0]
        # Extract JSON from log message (format: "INFO:logger_name:json_data")
        json_start = log_message.index('{')
        log_data = json.loads(log_message[json_start:])
        
        # Verify log data
        self.assertEqual(log_data['event'], 'import_start')
        self.assertEqual(log_data['admin_user'], 'testadmin')
        self.assertEqual(log_data['admin_user_id'], self.user.id)
        self.assertEqual(log_data['target_surveys'], ['Test Survey'])
        self.assertEqual(log_data['survey_count'], 1)
        self.assertEqual(log_data['source'], 'CSV upload')
        self.assertIn('timestamp', log_data)

    def test_log_start_with_multiple_surveys(self):
        """Test that log_start handles multiple surveys correctly."""
        from esp.survey.importers import ImportLogger
        import json
        
        # Create additional surveys
        survey2 = Survey.objects.create(
            name='Survey 2',
            program=self.program,
            category='teach',
        )
        survey3 = Survey.objects.create(
            name='Survey 3',
            program=self.program,
            category='learn',
        )
        
        with self.assertLogs('esp.survey.import', level='INFO') as cm:
            logger = ImportLogger()
            logger.log_start(self.user, [self.survey, survey2, survey3], 'Template: student_feedback')
        
        # Parse log data
        log_message = cm.output[0]
        json_start = log_message.index('{')
        log_data = json.loads(log_message[json_start:])
        
        # Verify multiple surveys logged
        self.assertEqual(log_data['survey_count'], 3)
        self.assertEqual(len(log_data['target_surveys']), 3)
        self.assertIn('Test Survey', log_data['target_surveys'])
        self.assertIn('Survey 2', log_data['target_surveys'])
        self.assertIn('Survey 3', log_data['target_surveys'])

    def test_log_complete_creates_log_entry(self):
        """Test that log_complete creates a log entry with counts."""
        from esp.survey.importers import ImportLogger
        import json
        
        with self.assertLogs('esp.survey.import', level='INFO') as cm:
            logger = ImportLogger()
            logger.log_complete(created=5, updated=2, skipped=1)
        
        # Parse log data
        log_message = cm.output[0]
        json_start = log_message.index('{')
        log_data = json.loads(log_message[json_start:])
        
        # Verify log data
        self.assertEqual(log_data['event'], 'import_complete')
        self.assertEqual(log_data['status'], 'success')
        self.assertEqual(log_data['questions_created'], 5)
        self.assertEqual(log_data['questions_updated'], 2)
        self.assertEqual(log_data['questions_skipped'], 1)
        self.assertEqual(log_data['total_processed'], 8)
        self.assertIn('timestamp', log_data)

    def test_log_failure_creates_error_log(self):
        """Test that log_failure creates an error log entry."""
        from esp.survey.importers import ImportLogger, ValidationError
        import json
        
        errors = [
            ValidationError(row_number=2, field='question_type', message='Invalid type'),
            ValidationError(row_number=3, field='question_name', message='Name too long'),
        ]
        
        with self.assertLogs('esp.survey.import', level='ERROR') as cm:
            logger = ImportLogger()
            logger.log_failure(errors)
        
        # Parse log data
        log_message = cm.output[0]
        json_start = log_message.index('{')
        log_data = json.loads(log_message[json_start:])
        
        # Verify log data
        self.assertEqual(log_data['event'], 'import_failure')
        self.assertEqual(log_data['status'], 'failed')
        self.assertEqual(log_data['error_count'], 2)
        self.assertEqual(len(log_data['errors']), 2)
        self.assertIn('Row 2, question_type: Invalid type', log_data['errors'][0])
        self.assertIn('Row 3, question_name: Name too long', log_data['errors'][1])
        self.assertIn('timestamp', log_data)

    def test_log_failure_with_string_errors(self):
        """Test that log_failure handles string error messages."""
        from esp.survey.importers import ImportLogger
        import json
        
        errors = [
            'Template file not found',
            'Database connection error',
        ]
        
        with self.assertLogs('esp.survey.import', level='ERROR') as cm:
            logger = ImportLogger()
            logger.log_failure(errors)
        
        # Parse log data
        log_message = cm.output[0]
        json_start = log_message.index('{')
        log_data = json.loads(log_message[json_start:])
        
        # Verify log data
        self.assertEqual(log_data['error_count'], 2)
        self.assertIn('Template file not found', log_data['errors'])
        self.assertIn('Database connection error', log_data['errors'])

    def test_log_start_with_no_user(self):
        """Test that log_start handles None user gracefully."""
        from esp.survey.importers import ImportLogger
        import json
        
        with self.assertLogs('esp.survey.import', level='INFO') as cm:
            logger = ImportLogger()
            logger.log_start(None, [self.survey], 'CSV upload')
        
        # Parse log data
        log_message = cm.output[0]
        json_start = log_message.index('{')
        log_data = json.loads(log_message[json_start:])
        
        # Verify user is logged as 'unknown'
        self.assertEqual(log_data['admin_user'], 'unknown')
        self.assertIsNone(log_data['admin_user_id'])

    def test_json_format_is_valid(self):
        """Test that all log entries produce valid JSON."""
        from esp.survey.importers import ImportLogger, ValidationError
        import json
        
        logger = ImportLogger()
        
        # Test log_start
        with self.assertLogs('esp.survey.import', level='INFO') as cm:
            logger.log_start(self.user, [self.survey], 'test')
        json_start = cm.output[0].index('{')
        json.loads(cm.output[0][json_start:])  # Should not raise
        
        # Test log_complete
        with self.assertLogs('esp.survey.import', level='INFO') as cm:
            logger.log_complete(1, 2, 3)
        json_start = cm.output[0].index('{')
        json.loads(cm.output[0][json_start:])  # Should not raise
        
        # Test log_failure
        with self.assertLogs('esp.survey.import', level='ERROR') as cm:
            logger.log_failure(['error'])
        json_start = cm.output[0].index('{')
        json.loads(cm.output[0][json_start:])  # Should not raise

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

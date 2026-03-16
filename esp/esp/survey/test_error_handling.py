"""
Tests for comprehensive error handling in survey question import.
Tests file upload errors, database errors, and CSV format errors.
"""
import io

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import override_settings

from esp.program.models import Program
from esp.survey.models import Survey, QuestionType, Question
from esp.survey.importers import CSVQuestionImporter
from esp.tests.util import CacheFlushTestCase as TestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class FileUploadErrorHandlingTest(TestCase):
    """Tests for file upload error handling."""
    
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

    def test_empty_file_error(self):
        """Test that empty file is handled with appropriate error."""
        csv_data = ""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Should raise ValueError for empty file
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        self.assertIn('empty', str(context.exception).lower())

    def test_file_with_only_whitespace(self):
        """Test that file with only whitespace is handled."""
        csv_data = "   \n\n   \n"
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        self.assertIn('empty', str(context.exception).lower())


class CSVFormatErrorHandlingTest(TestCase):
    """Tests for CSV format error handling."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        self.qt = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )

    def test_missing_required_columns_error(self):
        """Test that missing required columns produces descriptive error."""
        csv_data = """question_name
Missing type column"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        error_msg = str(context.exception)
        self.assertIn('Missing required columns', error_msg)
        self.assertIn('question_type', error_msg)

    def test_multiple_missing_columns_error(self):
        """Test that all missing columns are listed in error."""
        csv_data = """param_values
Just one column"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        error_msg = str(context.exception)
        self.assertIn('Missing required columns', error_msg)
        self.assertIn('question_name', error_msg)
        self.assertIn('question_type', error_msg)

    def test_malformed_csv_error(self):
        """Test that malformed CSV produces descriptive error."""
        # CSV with unclosed quote
        csv_data = """question_name,question_type
"Unclosed quote,Yes/No"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        # Should handle malformed CSV gracefully
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        # Error should mention CSV or parsing issue
        error_msg = str(context.exception).lower()
        self.assertTrue('csv' in error_msg or 'parsing' in error_msg or 'malformed' in error_msg)

    def test_encoding_error_utf16(self):
        """Test that UTF-16 encoded files are handled."""
        csv_data = "question_name,question_type\nTest Question,Yes/No"
        csv_bytes = csv_data.encode('utf-16')
        
        # Create a file-like object with UTF-16 encoded data
        csv_file = io.BytesIO(csv_bytes)
        
        importer = CSVQuestionImporter(csv_file, self.survey)
        
        # Should successfully parse UTF-16 encoded file
        questions = importer.parse_questions()
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_name, 'Test Question')

    def test_encoding_error_latin1(self):
        """Test that Latin-1 encoded files are handled."""
        csv_data = "question_name,question_type\nTest Question,Yes/No"
        csv_bytes = csv_data.encode('latin-1')
        
        # Create a file-like object with Latin-1 encoded data
        csv_file = io.BytesIO(csv_bytes)
        
        importer = CSVQuestionImporter(csv_file, self.survey)
        
        # Should successfully parse Latin-1 encoded file
        questions = importer.parse_questions()
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_name, 'Test Question')

    def test_unsupported_encoding_error(self):
        """Test that unsupported encoding produces descriptive error."""
        # Create data with invalid encoding (not UTF-8, UTF-16, or Latin-1)
        # Use a byte sequence that's invalid in all three encodings
        csv_bytes = b'\xff\xfe\xfd\xfc'
        
        csv_file = io.BytesIO(csv_bytes)
        
        importer = CSVQuestionImporter(csv_file, self.survey)
        
        with self.assertRaises(ValueError) as context:
            importer.parse_questions()
        
        error_msg = str(context.exception)
        self.assertIn('decode', error_msg.lower())


class DatabaseErrorHandlingTest(TestCase):
    """Tests for database error handling."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        self.qt = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )

    def test_foreign_key_violation_error(self):
        """Test that foreign key violations are handled with descriptive error."""
        # Try to import with non-existent question type
        csv_data = """question_name,question_type
Test Question,NonExistentType"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        # Should fail validation before hitting database
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        
        # Error should mention the non-existent type
        error_msg = ' '.join(result.errors)
        self.assertIn('NonExistentType', error_msg)
        self.assertIn('does not exist', error_msg)

    def test_transaction_rollback_on_error(self):
        """Test that transaction is rolled back when error occurs."""
        # Create CSV with one valid and one invalid question
        csv_data = """question_name,question_type
Valid Question,Yes/No
Invalid Question,NonExistentType"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        initial_count = Question.objects.filter(survey=self.survey).count()
        
        result = importer.import_questions()
        
        # Import should fail
        self.assertFalse(result.success)
        
        # No questions should be created (transaction rolled back)
        final_count = Question.objects.filter(survey=self.survey).count()
        self.assertEqual(initial_count, final_count)


class ValidationErrorAggregationTest(TestCase):
    """Tests for validation error aggregation."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        self.qt = QuestionType.objects.create(
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

    def test_multiple_validation_errors_aggregated(self):
        """Test that multiple validation errors are aggregated before display."""
        # CSV with multiple errors
        csv_data = """question_name,question_type,per_class,sequence
,Yes/No,false,1
Question 2,NonExistentType,invalid,abc
Question 3 with a very long name that exceeds the maximum allowed length of 255 characters and should trigger a validation error because it is way too long and goes on and on and on and on and on and on and on and on and on and on and on and on and on and on,Yes/No,true,2"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        # Should fail with multiple errors
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 1)
        
        # Check that errors mention specific issues
        error_text = ' '.join(result.errors)
        self.assertIn('required', error_text.lower())  # Empty question name
        self.assertIn('does not exist', error_text.lower())  # Invalid type
        self.assertIn('per_class', error_text.lower())  # Invalid per_class
        self.assertIn('sequence', error_text.lower())  # Invalid sequence

    def test_validation_errors_include_row_numbers(self):
        """Test that validation errors include row numbers for traceability."""
        csv_data = """question_name,question_type
,Yes/No
Question 2,NonExistentType"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        self.assertFalse(result.success)
        
        # Errors should include row numbers
        error_text = ' '.join(result.errors)
        self.assertIn('Row 2', error_text)
        self.assertIn('Row 3', error_text)

    def test_validation_errors_include_field_names(self):
        """Test that validation errors include field names."""
        csv_data = """question_name,question_type,per_class
Question 1,Yes/No,invalid_value"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        self.assertFalse(result.success)
        
        # Error should mention the field name
        error_text = ' '.join(result.errors)
        self.assertIn('per_class', error_text)

    def test_all_rows_validated_before_import(self):
        """Test that all rows are validated before any import occurs."""
        # Create CSV with errors in different rows
        csv_data = """question_name,question_type,sequence
Question 1,Yes/No,1
Question 2,Yes/No,invalid
Question 3,NonExistentType,3"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        
        initial_count = Question.objects.filter(survey=self.survey).count()
        
        result = importer.import_questions()
        
        # Should fail validation
        self.assertFalse(result.success)
        
        # Should report errors for both row 2 and row 3
        error_text = ' '.join(result.errors)
        self.assertIn('Row 3', error_text)  # Invalid sequence
        self.assertIn('Row 4', error_text)  # Invalid type
        
        # No questions should be created
        final_count = Question.objects.filter(survey=self.survey).count()
        self.assertEqual(initial_count, final_count)


class ErrorMessageQualityTest(TestCase):
    """Tests for error message quality and clarity."""
    
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )
        self.qt = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )

    def test_error_message_is_descriptive(self):
        """Test that error messages are descriptive and actionable."""
        csv_data = """question_name,question_type
Question 1,NonExistentType"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        self.assertFalse(result.success)
        
        error_msg = result.errors[0]
        # Should mention the specific type that doesn't exist
        self.assertIn('NonExistentType', error_msg)
        # Should indicate it's a validation issue
        self.assertIn('does not exist', error_msg)

    def test_parameter_count_error_is_specific(self):
        """Test that parameter count errors specify expected vs actual."""
        qt_rating = QuestionType.objects.create(
            name='Rating',
            _param_names='min|max',
            is_numeric=True,
            is_countable=True,
        )
        
        csv_data = """question_name,question_type,param_values
Rating Question,Rating,1"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        self.assertFalse(result.success)
        
        error_msg = result.errors[0]
        # Should mention expected and actual parameter counts
        self.assertIn('2 parameters', error_msg)
        self.assertIn('1 provided', error_msg)

    def test_sequence_error_is_clear(self):
        """Test that sequence validation errors are clear."""
        csv_data = """question_name,question_type,sequence
Question 1,Yes/No,not_a_number"""
        
        importer = CSVQuestionImporter(csv_data, self.survey)
        result = importer.import_questions()
        
        self.assertFalse(result.success)
        
        error_msg = result.errors[0]
        # Should mention sequence and what's expected
        self.assertIn('Sequence', error_msg)
        self.assertIn('positive integer', error_msg)

"""
Tests for esp.survey.models
Source: esp/esp/survey/models.py

Tests ListField descriptor, Survey, SurveyResponse, QuestionType,
Question, and Answer models.
"""
import datetime

from django.contrib.auth.models import Group

from esp.program.models import Program
from esp.survey.models import (
    Answer,
    ListField,
    Question,
    QuestionType,
    Survey,
    SurveyResponse,
)
from esp.tests.util import CacheFlushTestCase as TestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class ListFieldTest(TestCase):
    """Test the ListField descriptor used in QuestionType."""

    def test_get_returns_tuple(self):
        qt = QuestionType.objects.create(
            name='Test Type',
            _param_names='a|b|c',
            is_numeric=False,
            is_countable=False,
        )
        self.assertEqual(qt.param_names, ('a', 'b', 'c'))

    def test_get_empty_string(self):
        qt = QuestionType.objects.create(
            name='Empty Params',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        result = qt.param_names
        self.assertIsInstance(result, tuple)

    def test_set(self):
        qt = QuestionType.objects.create(
            name='Settable',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        qt.param_names = ('x', 'y', 'z')
        self.assertEqual(qt._param_names, 'x|y|z')


class SurveyTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Test Survey',
            program=self.program,
            category='learn',
        )

    def test_str(self):
        result = str(self.survey)
        self.assertIn('Test Survey', result)

    def test_num_participants_zero(self):
        self.assertEqual(self.survey.num_participants(), 0)

    def test_num_participants_with_responses(self):
        # num_participants looks at the associated program's students() or teachers() method
        # based on the tag filters. We can mock students() to return a dictionary with a user.
        from unittest.mock import MagicMock
        self.program.students = MagicMock(return_value={'test_filter': ['user1']})

        # We need to mock Tag.getProgramTag as well so it returns 'test_filter'
        from unittest.mock import patch
        with patch('esp.tagdict.models.Tag.getProgramTag', return_value='test_filter'):
            count = self.survey.num_participants()

        self.assertGreaterEqual(count, 1)


class SurveyResponseTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Response Survey',
            program=self.program,
            category='teach',
        )
        self.response = SurveyResponse.objects.create(survey=self.survey)

    def test_str(self):
        result = str(self.response)
        self.assertIsNotNone(result)

    def test_time_filled_auto(self):
        self.assertIsNotNone(self.response.time_filled)


class QuestionTypeTest(TestCase):
    def test_str_with_params(self):
        qt = QuestionType.objects.create(
            name='Rating',
            _param_names='min|max|step',
            is_numeric=True,
            is_countable=True,
        )
        result = str(qt)
        self.assertIn('Rating', result)

    def test_is_numeric(self):
        qt = QuestionType.objects.create(
            name='Numeric',
            _param_names='',
            is_numeric=True,
            is_countable=False,
        )
        self.assertTrue(qt.is_numeric)

    def test_is_countable(self):
        qt = QuestionType.objects.create(
            name='Countable',
            _param_names='',
            is_numeric=False,
            is_countable=True,
        )
        self.assertTrue(qt.is_countable)


class QuestionTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='Q Survey',
            program=self.program,
            category='learn',
        )
        self.qt = QuestionType.objects.create(
            name='Yes/No',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.question = Question.objects.create(
            survey=self.survey,
            name='Do you like it?',
            question_type=self.qt,
            _param_values='',
            seq=1,
        )

    def test_str(self):
        result = str(self.question)
        self.assertIn('Do you like it?', result)

    def test_get_params(self):
        params = self.question.get_params()
        self.assertIsInstance(params, dict)


class AnswerTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='A Survey',
            program=self.program,
            category='learn',
        )
        self.qt = QuestionType.objects.create(
            name='Free',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.question = Question.objects.create(
            survey=self.survey,
            name='Comments?',
            question_type=self.qt,
            _param_values='',
            seq=1,
        )
        self.response = SurveyResponse.objects.create(survey=self.survey)
        self.answer = Answer.objects.create(
            survey_response=self.response,
            question=self.question,
            value='test answer',
        )

    def test_str(self):
        result = str(self.answer)
        self.assertIsNotNone(result)

    def test_answer_property_setter_and_getter(self):
        self.answer.answer = 'New answer'
        self.answer.save()
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.answer, 'New answer')


class CSVImportTest(TestCase):
    """Test the parse_csv utility function for CSV survey question import."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.survey = Survey.objects.create(
            name='CSV Test Survey',
            program=self.program,
            category='learn',
        )
        self.qt_yesno = QuestionType.objects.create(
            name='test yes-no response',
            _param_names='',
            is_numeric=False,
            is_countable=False,
        )
        self.qt_rating = QuestionType.objects.create(
            name='test numeric rating',
            _param_names='Number of ratings|Lower text|Upper text',
            is_numeric=True,
            is_countable=True,
        )

    def _make_csv_file(self, content):
        """Create a file-like object from CSV string content."""
        import io
        return io.BytesIO(content.encode('utf-8'))

    def test_csv_parse_valid(self):
        """Valid CSV with all columns produces correct parsed rows."""
        from esp.program.modules.forms.surveys import parse_csv

        csv_content = (
            'question_text,question_type,per_class,seq,param_values\n'
            'Do you like it?,test yes-no response,false,1,\n'
            'Rate the class,test numeric rating,true,2,5|Low|High\n'
        )
        parsed_rows, errors = parse_csv(self._make_csv_file(csv_content))
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(parsed_rows), 2)
        self.assertEqual(parsed_rows[0]['question_text'], 'Do you like it?')
        self.assertEqual(parsed_rows[0]['question_type'], self.qt_yesno)
        self.assertFalse(parsed_rows[0]['per_class'])
        self.assertEqual(parsed_rows[0]['seq'], 1)
        self.assertEqual(parsed_rows[1]['question_text'], 'Rate the class')
        self.assertEqual(parsed_rows[1]['question_type'], self.qt_rating)
        self.assertTrue(parsed_rows[1]['per_class'])
        self.assertEqual(parsed_rows[1]['param_values'], '5|Low|High')

    def test_csv_parse_missing_required_column(self):
        """CSV missing question_text column returns header-level error."""
        from esp.program.modules.forms.surveys import parse_csv

        csv_content = 'question_type,per_class,seq\nyes-no response,false,1\n'
        parsed_rows, errors = parse_csv(self._make_csv_file(csv_content))
        self.assertEqual(len(parsed_rows), 0)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['row_number'], 0)
        self.assertIn('question_text', errors[0]['message'])

    def test_csv_parse_invalid_question_type(self):
        """Unrecognized question_type is flagged as error."""
        from esp.program.modules.forms.surveys import parse_csv

        csv_content = (
            'question_text,question_type\n'
            'Some question,nonexistent_type\n'
        )
        parsed_rows, errors = parse_csv(self._make_csv_file(csv_content))
        self.assertEqual(len(parsed_rows), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn('nonexistent_type', errors[0]['message'])

    def test_csv_parse_invalid_per_class(self):
        """Non-boolean per_class value is flagged as error."""
        from esp.program.modules.forms.surveys import parse_csv

        csv_content = (
            'question_text,question_type,per_class\n'
            'Some question,yes-no response,maybe\n'
        )
        parsed_rows, errors = parse_csv(self._make_csv_file(csv_content))
        self.assertEqual(len(parsed_rows), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn('per_class', errors[0]['message'])

    def test_csv_parse_partial_errors(self):
        """Mix of valid/invalid rows: valid rows succeed, invalid rows reported."""
        from esp.program.modules.forms.surveys import parse_csv

        csv_content = (
            'question_text,question_type,per_class,seq\n'
            'Good question,yes-no response,false,1\n'
            ',yes-no response,false,2\n'
            'Another good one,numeric rating,true,3\n'
        )
        parsed_rows, errors = parse_csv(self._make_csv_file(csv_content))
        self.assertEqual(len(parsed_rows), 2)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['row_number'], 3)
        self.assertIn('question_text is empty', errors[0]['message'])


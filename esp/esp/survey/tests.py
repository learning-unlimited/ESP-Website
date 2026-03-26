"""
Tests for esp.survey

- Model tests: ListField descriptor, Survey, SurveyResponse, QuestionType, Question, Answer
- CSV Import tests: parse_csv utility function for bulk question import
- View tests: Cross-program teacher survey responses page
"""
import datetime

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from unittest.mock import MagicMock, patch

from esp.program.models import Program
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModuleObj
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


# ===== Model Tests =====

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
        self.program.students = MagicMock(return_value={'test_filter': ['user1']})
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


# ===== CSV Import Tests =====

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


# ===== View Tests (cross-program teacher survey page, #3228) =====

class TeacherSurveyAllTest(ProgramFrameworkTest):
    """Tests for the cross-program teacher survey responses page."""

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 3, 'classes_per_teacher': 1, 'sections_per_class': 1,
            'num_rooms': 6,
        })
        super().setUp(*args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()

        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Create a student survey with per-class questions
        self.survey, _ = Survey.objects.get_or_create(
            name='Test Student Survey', program=self.program, category='learn')
        text_qtype, _ = QuestionType.objects.get_or_create(name='yes-no response')
        number_qtype, _ = QuestionType.objects.get_or_create(
            name='numeric rating', is_numeric=True, is_countable=True,
            _param_names="Number of ratings|Lower text|Middle text|Upper text")

        self.question_perclass, _ = Question.objects.get_or_create(
            survey=self.survey, name='Was this class good?',
            question_type=text_qtype, per_class=True, seq=0)
        self.question_rating, _ = Question.objects.get_or_create(
            survey=self.survey, name='Rate this class',
            question_type=number_qtype, per_class=True, seq=1,
            _param_values="5|Terrible|Okay|Awesome")

        # Pick a teacher and a section they teach
        self.teacher = self.teachers[0]
        self.section = self.teacher.getTaughtSections(self.program)[0]

        # Create a survey response with answers targeting this section
        self.response = SurveyResponse.objects.create(survey=self.survey)
        section_ct = ContentType.objects.get_for_model(self.section)
        Answer.objects.create(
            survey_response=self.response,
            question=self.question_perclass,
            content_type=section_ct,
            object_id=self.section.id,
            value='Yes', value_type="<class 'str'>")
        Answer.objects.create(
            survey_response=self.response,
            question=self.question_rating,
            content_type=section_ct,
            object_id=self.section.id,
            value='4', value_type="<class 'str'>")

    def test_teacher_sees_own_responses(self):
        """A teacher can view their own aggregated survey responses."""
        self.client.login(username=self.teacher.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn('All Survey Responses', content)
        self.assertIn(self.teacher.name(), content)
        self.assertIn(self.program.niceName(), content)
        self.assertIn('Was this class good?', content)

    def test_anonymous_user_redirected(self):
        """Anonymous users should be redirected to login."""
        self.client.logout()
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())

    def test_admin_sees_teacher_search(self):
        """An admin sees the teacher search form."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn('Search for a teacher', content)

    def test_admin_search_for_teacher(self):
        """Admin can search for a specific teacher via teacher_id GET param."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.get('/myesp/survey_responses?teacher_id=%d' % self.teacher.id)
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn(self.teacher.name(), content)
        self.assertIn(self.program.niceName(), content)

    def test_teacher_no_surveys(self):
        """A teacher with no surveys sees a 'no responses' message."""
        other_teacher = self.teachers[2]
        # Delete all surveys for this teacher's sections
        self.survey.delete()
        self.client.login(username=other_teacher.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn('No survey responses found', content)

    def test_student_gets_error(self):
        """A student (non-teacher) should get an error."""
        student = self.students[0]
        self.client.login(username=student.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        # ESPError returns 500
        self.assertEqual(response.status_code, 500)

    def test_admin_search_invalid_teacher_id(self):
        """Invalid teacher_id is gracefully ignored."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.get('/myesp/survey_responses?teacher_id=notanumber')
        self.assertEqual(response.status_code, 200)

    def test_admin_search_nonexistent_teacher(self):
        """Non-existent teacher_id is gracefully ignored."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.get('/myesp/survey_responses?teacher_id=999999')
        self.assertEqual(response.status_code, 200)

    def test_summary_table_and_accordion_present(self):
        """The page includes the summary table and accordion elements."""
        self.client.login(username=self.teacher.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn('Overview', content)
        self.assertIn('summary-table', content)
        self.assertIn('Detailed Responses', content)
        self.assertIn('accordion-header', content)
        self.assertIn('Expand All', content)

    def test_summary_shows_rating_and_responses(self):
        """The summary table shows avg rating and response count."""
        self.client.login(username=self.teacher.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        content = str(response.content, encoding='UTF-8')
        # Our test setup created 1 response with rating 4
        self.assertIn('4.0', content)
        # Response count should be visible in the summary table cell
        self.assertIn('>1<', content)

    def test_admin_post_search_for_teacher(self):
        """Admin can search for a teacher via POST form."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.post('/myesp/survey_responses',
                                    {'target_user': self.teacher.id})
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn(self.teacher.name(), content)
        self.assertIn(self.program.niceName(), content)

    def test_admin_post_invalid_form(self):
        """Admin POST with invalid data shows form errors, not crash."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.post('/myesp/survey_responses',
                                    {'target_user': 'not-a-valid-id'})
        self.assertEqual(response.status_code, 200)

    def test_teacher_no_responses_but_survey_exists(self):
        """A teacher with sections and a survey but zero responses doesn't crash."""
        self.response.delete()
        self.client.login(username=self.teacher.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn('N/A', content)
        self.assertIn('0', content)


class TeacherSurveyMultiSectionTest(ProgramFrameworkTest):
    """Tests for multi-section class aggregation in the survey page."""

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 2, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
        })
        super().setUp(*args, **kwargs)
        self.add_student_profiles()
        self.schedule_randomly()

        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        self.survey, _ = Survey.objects.get_or_create(
            name='Multi-Section Survey', program=self.program, category='learn')
        number_qtype, _ = QuestionType.objects.get_or_create(
            name='numeric rating', is_numeric=True, is_countable=True,
            _param_names="Number of ratings|Lower text|Middle text|Upper text")

        self.question_rating, _ = Question.objects.get_or_create(
            survey=self.survey, name='Rate this class',
            question_type=number_qtype, per_class=True, seq=1,
            _param_values="5|Bad|OK|Great")

        self.teacher = self.teachers[0]
        self.sections = list(self.teacher.getTaughtSections(self.program).order_by('id'))
        assert len(self.sections) >= 2, "Need at least 2 sections for this test"

        section_ct = ContentType.objects.get_for_model(self.sections[0])

        # Section 1: rating 3
        resp1 = SurveyResponse.objects.create(survey=self.survey)
        Answer.objects.create(
            survey_response=resp1, question=self.question_rating,
            content_type=section_ct, object_id=self.sections[0].id,
            value='3', value_type="<class 'str'>")

        # Section 2: rating 5
        resp2 = SurveyResponse.objects.create(survey=self.survey)
        Answer.objects.create(
            survey_response=resp2, question=self.question_rating,
            content_type=section_ct, object_id=self.sections[1].id,
            value='5', value_type="<class 'str'>")

    def test_summary_aggregates_across_sections(self):
        """Summary shows one row per class with aggregated data, not per-section."""
        self.client.login(username=self.teacher.username, password='password')
        response = self.client.get('/myesp/survey_responses')
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')

        # Should show aggregated avg: (3+5)/2 = 4.0
        self.assertIn('4.0', content)

        # The class emailcode should appear only once in summary table
        emailcode = self.sections[0].parent_class.emailcode()
        summary_section = content.split('Detailed Responses')[0]
        self.assertEqual(summary_section.count(emailcode), 1,
                        "Class should appear exactly once in summary table")

        # Should show total 2 responses in the summary table
        self.assertIn('>2<', summary_section)

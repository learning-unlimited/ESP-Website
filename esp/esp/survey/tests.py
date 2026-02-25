"""
Tests for esp.survey
- Model tests: ListField descriptor, Survey, SurveyResponse, QuestionType, Question, Answer
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
from esp.users.models import ESPUser

import random


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


# ===== Model Tests (from main) =====

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
        text_qtype, _ = QuestionType.objects.get_or_create(
            name='yes-no response')
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
        response = self.client.get(
            '/myesp/survey_responses?teacher_id=%d' % self.teacher.id)
        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding='UTF-8')
        self.assertIn(self.teacher.name(), content)
        self.assertIn(self.program.niceName(), content)

    def test_teacher_no_surveys(self):
        """A teacher with no surveys sees a 'no responses' message."""
        other_teacher = self.teachers[2]
        # Delete all surveys for this teacher's sections
        self.survey.delete()
        self.client.login(
            username=other_teacher.username, password='password')
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
        response = self.client.get(
            '/myesp/survey_responses?teacher_id=notanumber')
        self.assertEqual(response.status_code, 200)

    def test_admin_search_nonexistent_teacher(self):
        """Non-existent teacher_id is gracefully ignored."""
        admin = self.admins[0]
        self.client.login(username=admin.username, password='password')
        response = self.client.get(
            '/myesp/survey_responses?teacher_id=999999')
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
        # Response count should be visible
        self.assertIn('1', content)

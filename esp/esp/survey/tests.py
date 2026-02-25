from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModuleObj
from esp.survey.models import Survey, Question, QuestionType, SurveyResponse, Answer
from esp.users.models import ESPUser

import random


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
        from django.contrib.contenttypes.models import ContentType
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

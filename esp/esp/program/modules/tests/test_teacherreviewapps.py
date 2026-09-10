"""
Behavioral tests for per-class application reviews.

A teacher who teaches two classes that the same student applied to must be
able to review that student once per class, rather than sharing a single
review between both classes.

Refs: #378
"""

from datetime import datetime, timedelta

from esp.program.models import (RegistrationType, StudentAppQuestion,
                                StudentAppResponse, StudentAppReview,
                                StudentApplication, StudentRegistration)
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Permission


class TeacherReviewAppsTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self):
        super().setUp()
        self.student = self.students[0]
        self.teacher = self.teachers[0]

        #   ProgramFrameworkTest gives every teacher classes_per_teacher
        #   classes, so this teacher has two classes to review the same
        #   student for.
        self.cls_a, self.cls_b = list(
            self.teacher.classsubject_set.filter(parent_program=self.program).order_by('id')[:2]
        )

        enrolled, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', defaults={'category': 'student'}
        )
        self.app = StudentApplication.objects.create(program=self.program, user=self.student)
        self.questions = {}
        for cls in (self.cls_a, self.cls_b):
            StudentRegistration.objects.get_or_create(
                user=self.student,
                section=cls.get_sections()[0],
                relationship=enrolled,
            )
            question = StudentAppQuestion.objects.create(
                subject=cls, question='Why %s?' % cls.title
            )
            self.app.questions.add(question)
            self.questions[cls.id] = question

        Permission.objects.create(
            user=self.teacher,
            permission_type='Teacher/AppReview',
            program=self.program,
            start_date=datetime.now() - timedelta(days=1),
        )

    def _review_url(self, cls):
        return self.get_module_url('teach', 'review_student') + \
               f'/{cls.id}?student={self.student.id}'

    def _add_response(self, cls, text='An answer.'):
        response = StudentAppResponse.objects.create(
            question=self.questions[cls.id], response=text, complete=True
        )
        self.app.responses.add(response)
        return response

    def test_review_student_creates_one_review_per_class(self):
        """Reviewing the same student for two classes creates two reviews."""
        self.login_as('teacher')
        for cls in (self.cls_a, self.cls_b):
            response = self.client.get(self._review_url(cls))
            self.assertEqual(response.status_code, 200)

        reviews = self.app.reviews.filter(reviewer=self.teacher)
        self.assertEqual(
            reviews.count(), 2,
            'A teacher of two applied-to classes should get one review per class'
        )
        self.assertEqual(
            set(reviews.values_list('class_subject_id', flat=True)),
            {self.cls_a.id, self.cls_b.id},
        )

    def test_review_student_reuses_the_review_for_that_class(self):
        """Revisiting the same class does not create a second review."""
        self.login_as('teacher')
        self.client.get(self._review_url(self.cls_a))
        self.client.get(self._review_url(self.cls_a))

        self.assertEqual(
            self.app.reviews.filter(reviewer=self.teacher, class_subject=self.cls_a).count(),
            1,
        )

    def test_roster_only_counts_the_review_for_that_class(self):
        """The roster marks a student reviewed only for the class reviewed."""
        review = StudentAppReview.objects.create(
            reviewer=self.teacher, class_subject=self.cls_a, score=10, comments=''
        )
        self.app.reviews.add(review)

        self.login_as('teacher')
        roster_url = self.get_module_url('teach', 'review_students')
        self.assertContains(self.client.get(f'{roster_url}/{self.cls_a.id}'), 'Score: 10')
        self.assertContains(self.client.get(f'{roster_url}/{self.cls_b.id}'), 'Not Reviewed')

    def test_get_rank_in_class_uses_the_review_for_that_class(self):
        """getRankInClass() reads the score for the class asked about."""
        for cls, score in ((self.cls_a, 10), (self.cls_b, 1)):
            self._add_response(cls)
            review = StudentAppReview.objects.create(
                reviewer=self.teacher, class_subject=cls, score=score, comments=''
            )
            self.app.reviews.add(review)

        self.assertEqual(ESPUser.getRankInClass(self.student, self.cls_a), 10)
        self.assertEqual(ESPUser.getRankInClass(self.student, self.cls_b), 1)

    def test_get_rank_in_class_ignores_unscored_reviews(self):
        """An unscored review (created just by opening the page) is not a score."""
        self._add_response(self.cls_a)
        review = StudentAppReview.objects.create(
            reviewer=self.teacher, class_subject=self.cls_a, comments=''
        )
        self.app.reviews.add(review)

        self.assertEqual(ESPUser.getRankInClass(self.student, self.cls_a, default=7), 7)

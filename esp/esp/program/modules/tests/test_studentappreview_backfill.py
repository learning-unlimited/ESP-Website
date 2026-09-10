"""
Tests for the migration that backfills StudentAppReview.class_subject.

The backfill only guesses when there is nothing to guess: a review is linked
to a class if the reviewer teaches exactly one of the classes the reviewed
application asked questions about.  Everything else stays null.

Refs: #378
"""

from importlib import import_module

from django.apps import apps as global_apps

from esp.program.models import (StudentAppQuestion, StudentAppReview,
                                StudentApplication)
from esp.program.tests import ProgramFrameworkTest

#   Migration modules start with a digit, so they can't be imported normally.
backfill = import_module(
    'esp.program.migrations.0045_backfill_studentappreview_class_subject'
).backfill_class_subject


class StudentAppReviewBackfillTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp()
        self.student = self.students[0]
        self.teacher, self.other_teacher = self.teachers[0], self.teachers[1]
        #   Two classes taught by self.teacher, one taught by self.other_teacher.
        self.cls_a, self.cls_b = list(
            self.teacher.classsubject_set.filter(parent_program=self.program).order_by('id')[:2]
        )
        self.cls_c = self.other_teacher.classsubject_set.filter(
            parent_program=self.program).order_by('id')[0]
        self.app = StudentApplication.objects.create(program=self.program, user=self.student)

    def _ask_about(self, cls):
        question = StudentAppQuestion.objects.create(subject=cls, question='Why?')
        self.app.questions.add(question)
        return question

    def _review_by(self, reviewer):
        review = StudentAppReview.objects.create(reviewer=reviewer, comments='')
        self.app.reviews.add(review)
        return review

    def _run_and_reload(self, review):
        backfill(global_apps, None)
        review.refresh_from_db()
        return review

    def test_single_applied_class_is_filled_in(self):
        self._ask_about(self.cls_c)
        review = self._review_by(self.other_teacher)
        self.assertEqual(self._run_and_reload(review).class_subject_id, self.cls_c.id)

    def test_the_reviewers_own_class_is_chosen(self):
        self._ask_about(self.cls_a)
        self._ask_about(self.cls_c)
        review = self._review_by(self.other_teacher)
        self.assertEqual(self._run_and_reload(review).class_subject_id, self.cls_c.id)

    def test_two_classes_by_the_same_teacher_stay_null(self):
        """This is the ambiguous case the issue is about; don't guess."""
        self._ask_about(self.cls_a)
        self._ask_about(self.cls_b)
        review = self._review_by(self.teacher)
        self.assertIsNone(self._run_and_reload(review).class_subject_id)

    def test_reviews_by_non_teachers_stay_null(self):
        """Director reviews aren't tied to a class."""
        self._ask_about(self.cls_a)
        review = self._review_by(self.admins[0])
        self.assertIsNone(self._run_and_reload(review).class_subject_id)

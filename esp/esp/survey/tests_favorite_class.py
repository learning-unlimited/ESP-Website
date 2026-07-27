"""
Tests for Favorite Class survey functionality
"""

from django.test import TestCase
from esp.survey.models import QuestionType


class FavoriteClassSurveyTestCase(TestCase):
    """
    Test that Favorite Class questions work in survey results
    without requiring an "overall rating" question.
    """

    def test_favorite_class_question_type_exists(self):
        """
        Test that the Favorite Class question type exists
        in the database.
        """
        favorite_class_type = QuestionType.objects.filter(
            name='Favorite Class'
        )
        self.assertGreater(
            favorite_class_type.count(), 0,
            "Favorite Class question type should exist"
        )

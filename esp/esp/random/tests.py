"""
Tests for esp.random.views
Source: esp/esp/random/views.py

Tests good_random_class(), main view, and ajax view.
"""
import json
from unittest.mock import patch, MagicMock

from django.db.models import Q
from django.test import RequestFactory

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.random.views import good_random_class, main, ajax


class GoodRandomClassTest(TestCase):
    """Tests for good_random_class() filtering logic"""

    @patch('esp.random.views.Tag')
    @patch('esp.random.views.ClassSubject')
    def test_no_constraints(self, mock_classsubject, mock_tag):

        mock_tag.getTag.return_value = '{}'
        mock_cls = MagicMock()
        mock_classsubject.objects.random_class.return_value = mock_cls

        result = good_random_class()

        expected_q = Q()
        mock_classsubject.objects.random_class.assert_called_once_with(expected_q)
        self.assertEqual(result, mock_cls)

    @patch('esp.random.views.Tag')
    @patch('esp.random.views.ClassSubject')
    def test_bad_program_name_excluded(self, mock_classsubject, mock_tag):

        mock_tag.getTag.return_value = json.dumps({
            'bad_program_names': ['TestProgram']
        })
        mock_cls = MagicMock()
        mock_classsubject.objects.random_class.return_value = mock_cls

        result = good_random_class()

        expected_q = Q() & ~Q(parent_program__name__icontains='TestProgram')
        mock_classsubject.objects.random_class.assert_called_once_with(expected_q)
        self.assertEqual(result, mock_cls)

    @patch('esp.random.views.Tag')
    @patch('esp.random.views.ClassSubject')
    def test_bad_title_excluded(self, mock_classsubject, mock_tag):
        """Classes with bad titles should be excluded."""
        mock_tag.getTag.return_value = json.dumps({
            'bad_titles': ['Lunch Period']
        })
        mock_cls = MagicMock()
        mock_classsubject.objects.random_class.return_value = mock_cls

        result = good_random_class()

        expected_q = Q() & ~Q(title__iexact='Lunch Period')
        mock_classsubject.objects.random_class.assert_called_once_with(expected_q)
        self.assertEqual(result, mock_cls)

    @patch('esp.random.views.Tag')
    @patch('esp.random.views.ClassSubject')
    def test_multiple_constraints_combined(self, mock_classsubject, mock_tag):

        mock_tag.getTag.return_value = json.dumps({
            'bad_program_names': ['TestProgram'],
            'bad_titles': ['Lunch Period']
        })
        mock_cls = MagicMock()
        mock_classsubject.objects.random_class.return_value = mock_cls

        result = good_random_class()

        expected_q = Q() & ~Q(parent_program__name__icontains='TestProgram') & ~Q(title__iexact='Lunch Period')
        mock_classsubject.objects.random_class.assert_called_once_with(expected_q)
        self.assertEqual(result, mock_cls)


class MainViewTest(TestCase):
    """Tests for main() view."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    @patch('esp.random.views.good_random_class')
    def test_main_returns_200(self, mock_good_random_class):

        mock_cls = MagicMock()
        mock_good_random_class.return_value = mock_cls

        request = self.factory.get('/random/')
        response = main(request)

        self.assertEqual(response.status_code, 200)


class AjaxViewTest(TestCase):
    """Tests for ajax() view."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    @patch('esp.random.views.good_random_class')
    def test_ajax_returns_json(self, mock_good_random_class):

        mock_cls = MagicMock()
        mock_cls.title = 'Test Class'
        mock_cls.parent_program.niceName.return_value = 'Test Program'
        mock_cls.class_info = 'Some info'
        mock_good_random_class.return_value = mock_cls

        request = self.factory.get('/random/ajax')
        response = ajax(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'Test Class')
        self.assertEqual(data['program'], 'Test Program')
        self.assertEqual(data['info'], 'Some info')

import json

from django.test import RequestFactory

from esp.program.models import ClassSubject
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.random.views import good_random_class, main, ajax

class RandomModuleTests(ProgramFrameworkTest):
    def setUp(self):
        super(RandomModuleTests, self).setUp(
            num_categories=2,
            num_teachers=2,
            classes_per_teacher=2,
            sections_per_class=1,
            num_students=1,
        )
        self.factory = RequestFactory()

        # grabbing generated classes for constraints
        self.class1 = ClassSubject.objects.all()[0]
        self.class2 = ClassSubject.objects.all()[1]
        self.program_name = self.program.name

        # blacklist class2 but keep class1
        constraints = {
            "bad_program_names": ["Some Totally Unknown Program"],
            "bad_titles": [self.class2.title]
        }
        Tag.setTag('random_constraints', value=json.dumps(constraints))

    def test_good_random_class(self):
        """make sure good_random_class respects tag constraints"""
        # check if program blacklist works
        constraints = {
            "bad_program_names": [self.program_name], # block all programs
            "bad_titles": []
        }
        Tag.setTag('random_constraints', value=json.dumps(constraints))
        cls = good_random_class()
        self.assertIsNone(cls)

        # now testing title blacklists
        constraints = {
            "bad_program_names": [],
            "bad_titles": [c.title for c in ClassSubject.objects.exclude(id=self.class1.id)]
        }
        Tag.setTag('random_constraints', value=json.dumps(constraints))
        cls = good_random_class()
        self.assertIsNotNone(cls)
        self.assertEqual(cls.title, self.class1.title)

    def test_good_random_class_empty_constraints(self):
        """test good_random_class when constraints exist but are empty"""
        Tag.setTag('random_constraints', value=json.dumps({}))
        cls = good_random_class()
        # any class can be returned here
        self.assertIsNotNone(cls)

    def test_good_random_class_missing_tag(self):
        """test what happens when tag is missing entirely"""
        Tag.unSetTag('random_constraints')

        # it should safely return a valid class
        # previously this threw JSONDecodeError/TypeError bc getTag returned None
        cls = good_random_class()
        self.assertIsNotNone(cls)

    def test_main_view(self):
        """test main view returns 200 ok"""
        request = self.factory.get('/random')
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

    def test_ajax_view(self):
        """test ajax view returns expected json keys"""

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

        response_data = json.loads(response.content.decode('utf-8'))

        # check standard json keys
        self.assertIn('title', response_data)
        self.assertIn('program', response_data)
        self.assertIn('info', response_data)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'Test Class')
        self.assertEqual(data['program'], 'Test Program')
        self.assertEqual(data['info'], 'Some info')

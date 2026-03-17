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
        response = main(request)

        self.assertEqual(response.status_code, 200)

    def test_ajax_view(self):
        """test ajax view returns expected json keys"""
        request = self.factory.get('/random/ajax')
        response = ajax(request)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content.decode('utf-8'))

        # check standard json keys
        self.assertIn('title', response_data)
        self.assertIn('program', response_data)
        self.assertIn('info', response_data)

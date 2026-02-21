import json

from django.template import Template, Context

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ClassSubject
from esp.users.models import ESPUser


class ClassSearchModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(ClassSearchModuleTest, self).setUp(*args, **kwargs)
        self.program.getModules()
        self.schedule_randomly()
        pm = ProgramModule.objects.get(handler='ClassSearchModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.qb = self.module.query_builder()

        self.admin, created = ESPUser.objects.get_or_create(username='admin')
        self.admin.set_password('password')
        self.admin.makeAdmin()

    def test_can_render(self):
        rendered = Template("""
            {% load query_builder %}
            {% render_query_builder qb %}
        """).render(Context({'qb': self.qb}))
        self.assertIn("sections scheduled", rendered)
        self.assertIn("the status", rendered)

    def test_can_search(self):
        qs = self.qb.as_queryset({
            'filter': 'status',
            'negated': True,
            'values': ['-10'],
        })
        # Who knows how long it will be, that depends on other tests, but I
        # would really hope that after schedule_randomly() has run, there will
        # be a class that isn't rejected, no matter what happened on the way.
        self.assertGreater(len(qs), 0)
        for cs in qs:
            self.assertIsInstance(qs[0], ClassSubject)
            self.assertEqual(qs[0].parent_program, self.program)

    def test_render_in_page(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/classsearch/')
        self.assertContains(r, "sections scheduled")
        self.assertContains(r, "the status")

    def test_results_page(self):
        self.client.login(username='admin', password='password')
        query = json.dumps({
            'filter': 'status',
            'negated': True,
            'values': ['-10'],
        })
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'query': query})
        self.assertContains(r, "Course Description")
        self.assertContains(r, "Room Request")
        self.assertContains(r, "Edit Teacher List")

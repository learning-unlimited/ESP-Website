import json

from django.template import Template, Context
from django.test import RequestFactory

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ClassSubject
from esp.users.models import ESPUser


class ClassSearchModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
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

    def simple_search_query(self, **params):
        """Run the module's form-to-query translation on the given params."""
        request = RequestFactory().get(
            '/manage/' + self.program.url + '/classsearch/', params)
        form_context = self.module.simple_search_context(request, self.program)
        return self.module.simple_search_query(request, form_context)

    def test_simple_search_query(self):
        """The simple search form should become an AND of query builder filters."""
        self.assertIsNone(self.simple_search_query())
        self.assertIsNone(self.simple_search_query(
            s_title='', s_teacher='', s_category='', s_status='',
            s_grade_min='', s_grade_max=''))

        query = self.simple_search_query(
            s_title='Test class 3', s_teacher='', s_category='',
            s_status='10', s_grade_min='7', s_grade_max='')
        self.assertEqual(query, {
            'filter': 'and',
            'negated': False,
            'values': [
                {'filter': 'title', 'negated': False,
                 'values': ['Test class 3']},
                {'filter': 'status', 'negated': False, 'values': ['10']},
                {'filter': 'grade', 'negated': False, 'values': ['7', '']},
            ],
        })
        #   The query it builds has to be one the query builder can run.
        self.assertEqual([cls.title for cls in self.qb.as_queryset(query)],
                         ['Test class 3'])

    def test_simple_search_ignores_bad_values(self):
        """Values the form never offered should be dropped, not searched for.

        The query builder raises (and emails the admins) on an unrecognized
        choice, so a hand-edited querystring must not reach it.
        """
        self.assertIsNone(self.simple_search_query(
            s_category='not a number', s_status='not a status',
            s_grade_min='0', s_grade_max='99'))

        #   A bad value alongside a good one drops only the bad one.
        query = self.simple_search_query(s_title='Test class 3',
                                         s_category='not a number')
        self.assertEqual(query['values'],
                         [{'filter': 'title', 'negated': False,
                           'values': ['Test class 3']}])

    def test_simple_search_bad_values_page(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'s_category': 'not a number'})
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Test class 3")

    def test_simple_search_page(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'s_title': 'Test class 3'})
        self.assertContains(r, "Test class 3")
        self.assertNotContains(r, "Test class 4")
        #   The query builder should be preloaded with the equivalent query so
        #   that the search can be refined there.
        self.assertContains(r, '"filter": "and"')

    def test_simple_search_by_teacher(self):
        """Teacher usernames should match regardless of case."""
        self.client.login(username='admin', password='password')
        teacher = self.teachers[0]
        titles = sorted(cls.title for cls in
                        self.program.classes().filter(teachers=teacher))
        self.assertGreater(len(titles), 0)
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'s_teacher': teacher.username.upper()})
        for title in titles:
            self.assertContains(r, title)

    def test_simple_search_no_results(self):
        """An empty simple search result should say so, not render silently."""
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'s_title': 'no such class'})
        self.assertContains(r, "No classes were found")

    def test_simple_search_empty_form(self):
        """Submitting the form with nothing filled in shouldn't search."""
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'s_title': '', 's_teacher': '', 's_category': '',
                             's_status': '', 's_grade_min': '', 's_grade_max': ''})
        self.assertNotContains(r, "No classes were found")
        self.assertNotContains(r, "Test class 3")

    def test_advanced_search_stays_available(self):
        """The advanced query builder must never be hidden with no way back.

        It lives in a Bootstrap 5 collapse, which needs `show` to start open
        and `data-bs-toggle` for the toggle to do anything at all.
        """
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/classsearch/')
        self.assertContains(r, 'data-bs-toggle="collapse"')
        self.assertContains(r, 'class="collapse show"')

        #   After a simple search it starts collapsed, but must still be
        #   expandable.
        r = self.client.get('/manage/' + self.program.url + '/classsearch/',
                            {'s_title': 'Test class 3'})
        self.assertContains(r, 'data-bs-toggle="collapse"')
        self.assertContains(r, "sections scheduled")

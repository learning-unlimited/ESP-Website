import json

from django.template import Template, Context

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.middleware import ESPError
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ClassSubject
from esp.program.models.flags import ClassFlag, ClassFlagType
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
        self.assertIn("flag creator", rendered)

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

    def test_flag_creator_filter(self):
        # setup flag types and flags
        flag_type = ClassFlagType.objects.create(name='Test Flag %s' % self.program.id)
        self.program.flag_types.add(flag_type)
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        user_a = self.admin
        user_b, _ = ESPUser.objects.get_or_create(username='otheruser')
        ClassFlag.objects.create(subject=cls, flag_type=flag_type, comment='a',
                                 created_by=user_a, modified_by=user_a)
        ClassFlag.objects.create(subject=cls, flag_type=flag_type, comment='b',
                                 created_by=user_b, modified_by=user_b)

        query = {
            'filter': 'flag_creator',
            'negated': False,
            'values': [{'id': user_a.id, 'username': user_a.username}],
        }
        qs = self.qb.as_queryset(query)
        self.assertGreater(len(qs), 0)
        # Should include the class because at least one flag by user_a exists.
        self.assertIn(cls, qs)

    def test_ajaxflagusers_endpoint(self):
        self.client.login(username='admin', password='password')
        flag_type = ClassFlagType.objects.create(name='Test Flag 2 %s' % self.program.id)
        self.program.flag_types.add(flag_type)
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        ClassFlag.objects.create(subject=cls, flag_type=flag_type, comment='c',
                                 created_by=self.admin, modified_by=self.admin)
        r = self.client.get('/manage/' + self.program.url + '/ajaxflagusers', {'term': 'adm'})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content.decode('utf-8'))
        self.assertTrue(any(u['username'] == 'admin' for u in data))

    def test_flag_creator_rejects_invalid_selection(self):
        with self.assertRaises(ESPError):
            self.qb.as_queryset({
                'filter': 'flag_creator',
                'negated': False,
                'values': ['not-a-dict'],
            })

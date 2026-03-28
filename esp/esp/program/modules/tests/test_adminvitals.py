from unittest.mock import Mock

from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.adminvitals import KeyDoesNotExist
from esp.program.tests import ProgramFrameworkTest


class AdminVitalsTest(ProgramFrameworkTest):
    """Regression tests for the AdminVitals dashboard inline module."""

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'modules': [
                ProgramModule.objects.get(handler='AdminCore'),
                ProgramModule.objects.get(handler='AdminVitals'),
            ],
        })
        super(AdminVitalsTest, self).setUp(*args, **kwargs)

        pm = ProgramModule.objects.get(handler='AdminVitals')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

    def test_prepare_preserves_existing_dict_context(self):
        context = {'existing': 'value'}

        prepared = self.module.prepare(context)

        self.assertIs(prepared, context)
        self.assertEqual(prepared['existing'], 'value')

    def test_prepare_initializes_empty_context_for_none(self):
        prepared = self.module.prepare(None)

        self.assertEqual(prepared, {})
        prepared['modules'] = []
        self.assertEqual(prepared['modules'], [])

    def test_prepare_normalizes_plain_mock_context(self):
        mock_context = Mock(name='dashboard_context')

        try:
            prepared = self.module.prepare(mock_context)
        except KeyDoesNotExist:
            self.fail('AdminVitals.prepare() raised KeyDoesNotExist for a mock dashboard context')

        self.assertIsInstance(prepared, dict)
        self.assertIsNot(prepared, mock_context)
        prepared['modules'] = []
        self.assertEqual(prepared['modules'], [])

    def test_dashboard_renders_with_adminvitals_enabled(self):
        admin = self.admins[0]
        self.assertTrue(
            self.client.login(username=admin.username, password='password'),
            "Couldn't log in as admin %s" % admin.username,
        )

        response = self.client.get('/manage/%s/dashboard' % self.program.getUrlBase())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Program Vitals')

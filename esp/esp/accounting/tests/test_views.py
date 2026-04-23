from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import Group
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser
from esp.program.models import Program
from esp.accounting.controllers import (
    GlobalAccountingController,
    ProgramAccountingController,
    IndividualAccountingController,
)
from esp.accounting.views import user_accounting


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator',
                 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class SummaryViewTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.client = Client()
        self.admin = ESPUser.objects.create_user(
            username='admin', password='pass'
        )
        self.admin.makeRole('Administrator')
        self.student = ESPUser.objects.create_user(
            username='student', password='pass'
        )
        self.student.makeRole('Student')
        GlobalAccountingController().setup_accounts()

    def test_summary_admin_can_access(self):
        """Admin user gets 200 response from summary view."""
        self.client.login(username='admin', password='pass')
        response = self.client.get('/accounting/')
        self.assertEqual(response.status_code, 200)

    def test_summary_non_admin_blocked(self):
        """Non admin user is redirected from summary view."""
        self.client.login(username='student', password='pass')
        response = self.client.get('/accounting/')
        self.assertIn(response.status_code, [302, 403])

    def test_summary_not_logged_in_blocked(self):
        """Unauthenticated user cannot access summary view."""
        response = self.client.get('/accounting/')
        self.assertIn(response.status_code, [302, 403])


class UserSummaryViewTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.client = Client()
        self.admin = ESPUser.objects.create_user(
            username='admin', password='pass'
        )
        self.admin.makeRole('Administrator')
        self.student = ESPUser.objects.create_user(
            username='student', password='pass'
        )
        self.student.makeRole('Student')

    def test_user_summary_get_no_user_shows_form(self):
        """GET with no target_user shows empty search form."""
        self.client.login(username='admin', password='pass')
        response = self.client.get('/accounting/user')
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_user_summary_get_with_valid_user(self):
        """GET with valid target_user ID shows accounting."""
        self.client.login(username='admin', password='pass')
        response = self.client.get(
            '/accounting/user',
            {'target_user': self.student.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['target_user'], self.student
        )


class UserAccountingFunctionTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            grade_min=7, grade_max=12
        )
        self.student = ESPUser.objects.create_user(
            username='student', password='pass'
        )
        GlobalAccountingController().setup_accounts()
        pac = ProgramAccountingController(self.program)
        pac.setup_accounts()
        pac.setup_lineitemtypes(50.0)

    def test_user_accounting_empty_programs(self):
        """user_accounting returns empty list for no programs."""
        result = user_accounting(self.student, [])
        self.assertEqual(result, [])

    def test_user_accounting_returns_one_result(self):
        """user_accounting returns one result per program."""
        result = user_accounting(self.student, [self.program])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['program'], self.program)

    def test_user_accounting_has_identifier(self):
        """user_accounting result includes identifier string."""
        result = user_accounting(self.student, [self.program])
        self.assertIn('identifier', result[0])

    def test_user_accounting_after_payment(self):
        """user_accounting shows correct amounts after payment."""
        iac = IndividualAccountingController(
            self.program, self.student
        )
        iac.ensure_required_transfers()
        iac.submit_payment(Decimal('50.00'))
        result = user_accounting(self.student, [self.program])
        self.assertEqual(result[0]['paid'], Decimal('50.00'))
        self.assertEqual(result[0]['due'], Decimal('0.00'))   
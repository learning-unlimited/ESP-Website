from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.utils import timezone

from esp.program.models import Program, ProgramModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Permission


class AdminCoreSettingsTest(ProgramFrameworkTest):
    def setUp(self):
        modules = [ProgramModule.objects.get(handler='AdminCore')]
        super().setUp(modules=modules)

        self.adminUser, created = ESPUser.objects.get_or_create(username='admin_settings')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()

    def test_settings_view(self):
        from esp.accounting.controllers import ProgramAccountingController

        self.client.login(username='admin_settings', password='password')

        response = self.client.get(f"/manage/{self.program.url}/settings/program")
        self.assertEqual(response.status_code, 200)

        prog_form = None
        for label, name, form in response.context['forms']:
            if name == 'program':
                prog_form = form
                break

        self.assertIsNotNone(prog_form)
        prog_dict = prog_form.initial.copy()

        pac = ProgramAccountingController(self.program)
        pac.default_admission_lineitemtype()

        prog_dict['base_cost'] = 125
        prog_dict['sibling_discount'] = 25
        prog_dict['form_name'] = 'program'
        prog_dict['program_modules'] = [m.id for m in self.program.program_modules.all()]
        prog_dict['class_categories'] = [c.id for c in self.program.class_categories.all()]
        prog_dict['flag_types'] = [f.id for f in self.program.flag_types.all()]

        if not prog_dict.get('term'):
            prog_dict['term'] = self.program.program_instance
        if not prog_dict.get('term_friendly'):
            prog_dict['term_friendly'] = self.program.name.replace(self.program.program_type, '', 1).strip()
        prog_dict['program_type'] = self.program.program_type

        response = self.client.post(f"/manage/{self.program.url}/settings/program", prog_dict)
        self.assertIn(response.status_code, [200, 302])

        updated_prog = Program.objects.get(pk=self.program.pk)
        self.assertEqual(updated_prog.sibling_discount, 25)

        line_item = pac.default_admission_lineitemtype()
        line_item.refresh_from_db()
        self.assertEqual(line_item.amount_dec, Decimal('125.00'))


class AdminCoreDeadlineManagementTest(ProgramFrameworkTest):
    def setUp(self):
        modules = [ProgramModule.objects.get(handler='AdminCore')]
        super().setUp(modules=modules)

        self.adminUser, created = ESPUser.objects.get_or_create(username='admin_deadlines')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.client.login(username='admin_deadlines', password='password')

    def test_deadline_management_open_creates_new(self):
        """When no permission exists, open should create one with no end_date."""
        group = Group.objects.create(name='TestGroup')
        perm_type = 'StudentReg'

        url = f"/manage/{self.program.url}/deadline_management/open"
        response = self.client.get(url, {'group': group.id, 'perm': perm_type})
        self.assertEqual(response.status_code, 200)

        perm = Permission.objects.get(role=group, permission_type=perm_type, program=self.program)
        self.assertIsNone(perm.end_date)

    def test_deadline_management_open_unexpires_existing(self):
        """When a permission already exists with an end_date, open should clear it."""
        group = Group.objects.create(name='TestGroupReopen')
        perm_type = 'StudentReg'
        perm = Permission.objects.create(
            role=group,
            permission_type=perm_type,
            program=self.program,
            start_date=timezone.now(),
            end_date=timezone.now(),
        )

        url = f"/manage/{self.program.url}/deadline_management/open"
        response = self.client.get(url, {'group': group.id, 'perm': perm_type})
        self.assertEqual(response.status_code, 200)

        perm.refresh_from_db()
        self.assertIsNone(perm.end_date)

    def test_deadline_management_close(self):
        """Close should set end_date on the permission."""
        group = Group.objects.create(name='TestGroupClose')
        perm_type = 'StudentReg'
        Permission.objects.create(
            role=group,
            permission_type=perm_type,
            program=self.program,
            start_date=timezone.now(),
        )

        url = f"/manage/{self.program.url}/deadline_management/close"
        response = self.client.get(url, {'group': group.id, 'perm': perm_type})
        self.assertEqual(response.status_code, 200)

        perm = Permission.objects.get(role=group, permission_type=perm_type, program=self.program)
        self.assertIsNotNone(perm.end_date)

    def test_deadline_management_delete(self):
        """Delete should remove the permission entirely."""
        group = Group.objects.create(name='TestGroupDelete')
        perm_type = 'StudentReg'
        perm = Permission.objects.create(
            role=group,
            permission_type=perm_type,
            program=self.program,
            start_date=timezone.now(),
        )
        perm_id = perm.id

        url = f"/manage/{self.program.url}/deadline_management/delete"
        response = self.client.get(url, {'perm_id': perm_id})
        self.assertEqual(response.status_code, 200)

        self.assertFalse(Permission.objects.filter(id=perm_id).exists())


class AdminCoreWipeTestDataTest(ProgramFrameworkTest):
    def setUp(self):
        modules = [ProgramModule.objects.get(handler='AdminCore')]
        super().setUp(modules=modules)

        self.adminUser, created = ESPUser.objects.get_or_create(username='admin_wipe')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.client.login(username='admin_wipe', password='password')

        self.testUser = ESPUser.objects.create(username='test_user_wipe')

    def test_wipe_test_data_preview(self):
        """POST without confirmed=1 should return a preview, not execute."""
        url = f"/manage/{self.program.url}/wipe_test_data"
        with patch('esp.program.modules.handlers.admincore.TestDataCleanupController.execute') as mock_execute:
            response = self.client.post(url, {'username': 'test_user_wipe'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['preview'])
            self.assertEqual(response.context['target_user'], self.testUser)
            mock_execute.assert_not_called()

    def test_wipe_test_data_execute(self):
        """POST with confirmed=1 should delegate to TestDataCleanupController.execute."""
        url = f"/manage/{self.program.url}/wipe_test_data"
        with patch('esp.program.modules.handlers.admincore.TestDataCleanupController.execute') as mock_execute:
            response = self.client.post(url, {'username': 'test_user_wipe', 'confirmed': '1'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['success'])
            self.assertEqual(response.context['target_user'], self.testUser)
            mock_execute.assert_called_once()

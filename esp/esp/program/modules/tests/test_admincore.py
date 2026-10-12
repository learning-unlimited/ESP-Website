from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.utils import timezone

from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.models import ClassSection, ClassSubject, Program, ProgramModule, RegistrationType, StudentRegistration
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

        # Verify sibling discount line item type was also updated
        sibling_discount_line_item = pac.default_siblingdiscount_lineitemtype()
        if sibling_discount_line_item:
            sibling_discount_line_item.refresh_from_db()
            self.assertEqual(sibling_discount_line_item.amount_dec, Decimal('25.00'))


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
        perm_type = 'Student/Classes'

        url = f"/manage/{self.program.url}/deadline_management/open"
        response = self.client.get(url, {'group': group.id, 'perm': perm_type})
        self.assertEqual(response.status_code, 200)

        perm = Permission.objects.get(role=group, permission_type=perm_type, program=self.program)
        self.assertIsNone(perm.end_date)

    def test_deadline_management_open_unexpires_existing(self):
        """When a permission already exists with an end_date, open should clear it."""
        group = Group.objects.create(name='TestGroupReopen')
        perm_type = 'Student/Classes'
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
        perm_type = 'Student/Classes'
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
        perm_type = 'Student/Classes'
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
        with patch('esp.program.modules.handlers.admincore.DataCleanupController.execute') as mock_execute:
            response = self.client.post(url, {'username': 'test_user_wipe'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['preview'])
            self.assertEqual(response.context['target_user'], self.testUser)
            mock_execute.assert_not_called()

    def test_wipe_test_data_execute(self):
        """POST with confirmed=1 should delegate to DataCleanupController.execute."""
        url = f"/manage/{self.program.url}/wipe_test_data"
        with patch('esp.program.modules.handlers.admincore.DataCleanupController.execute') as mock_execute:
            response = self.client.post(url, {'username': 'test_user_wipe', 'confirmed': '1'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['success'])
            self.assertEqual(response.context['target_user'], self.testUser)
            mock_execute.assert_called_once()


class AdminCoreLunchConstraintsTest(ProgramFrameworkTest):
    def setUp(self):
        modules = [ProgramModule.objects.get(handler='AdminCore')]
        super().setUp(
            modules=modules,
            num_teachers=1,
            num_students=3,
            num_timeslots=3,
            timeslot_length=50,
        )
        self.add_user_profiles()
        self.adminUser, _ = ESPUser.objects.get_or_create(username='admin_lunch')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.client.login(username='admin_lunch', password='password')
        self.enrolled_rt, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', category='student'
        )

    def test_unoccupied_lunch_section_deleted_successfully(self):
        """Unoccupied lunch section is deleted and saved=True when unchecked."""
        ts = self.timeslots[0]
        lcg = LunchConstraintGenerator(self.program, [ts])
        lcg.generate_all_constraints()
        self.assertEqual(self.program.lunch_sections().count(), 1)

        url = f"/manage/{self.program.url}/lunch_constraints"
        response = self.client.post(url, {'timeslots': []})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['saved'])
        self.assertEqual(self.program.lunch_sections().count(), 0)
        self.assertFalse(
            ClassSubject.objects.filter(parent_program=self.program, category__is_lunch=True).exists()
        )

    def test_occupied_lunch_section_deletion_refused_with_error(self):
        """Occupied lunch section cannot be deleted; actionable error shown, box kept checked."""
        ts = self.timeslots[0]
        lcg = LunchConstraintGenerator(self.program, [ts])
        lcg.generate_all_constraints()
        lunch_sec = self.program.lunch_sections().first()

        StudentRegistration.objects.create(
            user=self.students[0], section=lunch_sec, relationship=self.enrolled_rt
        )
        lunch_sec.refresh_from_db()
        self.assertEqual(lunch_sec.num_students(), 1)

        url = f"/manage/{self.program.url}/lunch_constraints"
        response = self.client.post(url, {'timeslots': []})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['saved'])
        self.assertEqual(self.program.lunch_sections().count(), 1)
        self.assertTrue(
            StudentRegistration.objects.filter(section=lunch_sec, user=self.students[0]).exists()
        )

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        msg_text = str(messages[0])
        self.assertIn("Could not remove the", msg_text)
        self.assertIn("1 student is registered for it", msg_text)
        self.assertIn("Clear those registrations before changing this lunch section", msg_text)

        # The form should keep the occupied lunch timeslot checked
        form_timeslots = response.context['form']['timeslots'].value()
        self.assertIn(str(ts.id), form_timeslots)

    def test_multiple_occupied_lunch_sections_handled_clearly(self):
        """Multiple occupied lunch sections report clear errors and preserve all sections."""
        ts1, ts2 = self.timeslots[0], self.timeslots[1]
        lcg = LunchConstraintGenerator(self.program, [ts1, ts2])
        lcg.generate_all_constraints()
        secs = list(self.program.lunch_sections().order_by('id'))
        self.assertEqual(len(secs), 2)

        StudentRegistration.objects.create(
            user=self.students[0], section=secs[0], relationship=self.enrolled_rt
        )
        StudentRegistration.objects.create(
            user=self.students[1], section=secs[1], relationship=self.enrolled_rt
        )
        StudentRegistration.objects.create(
            user=self.students[2], section=secs[1], relationship=self.enrolled_rt
        )

        url = f"/manage/{self.program.url}/lunch_constraints"
        response = self.client.post(url, {'timeslots': []})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['saved'])
        self.assertEqual(self.program.lunch_sections().count(), 2)

        messages = [str(m) for m in response.context['messages']]
        self.assertEqual(len(messages), 2)
        self.assertTrue(any("1 student is registered" in m for m in messages))
        self.assertTrue(any("2 students are registered" in m for m in messages))

        form_timeslots = response.context['form']['timeslots'].value()
        self.assertIn(str(ts1.id), form_timeslots)
        self.assertIn(str(ts2.id), form_timeslots)

    def test_mixed_occupied_and_unoccupied_lunch_sections(self):
        """Unoccupied section is deleted while occupied section is preserved."""
        ts1, ts2 = self.timeslots[0], self.timeslots[1]
        lcg = LunchConstraintGenerator(self.program, [ts1, ts2])
        lcg.generate_all_constraints()
        secs = list(self.program.lunch_sections().order_by('id'))

        # Only sec 2 has enrolled students
        StudentRegistration.objects.create(
            user=self.students[0], section=secs[1], relationship=self.enrolled_rt
        )

        url = f"/manage/{self.program.url}/lunch_constraints"
        response = self.client.post(url, {'timeslots': []})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['saved'])

        # Section 1 was deleted, section 2 was preserved
        remaining_secs = list(self.program.lunch_sections())
        self.assertEqual(len(remaining_secs), 1)
        self.assertEqual(remaining_secs[0].id, secs[1].id)

        form_timeslots = response.context['form']['timeslots'].value()
        self.assertIn(str(ts2.id), form_timeslots)
        self.assertNotIn(str(ts1.id), form_timeslots)

    def test_clear_existing_constraints_returns_failed_objects(self):
        """Direct call to clear_existing_constraints returns failed sections and subjects."""
        ts = self.timeslots[0]
        lcg = LunchConstraintGenerator(self.program, [ts])
        lcg.generate_all_constraints()
        lunch_sec = self.program.lunch_sections().first()

        StudentRegistration.objects.create(
            user=self.students[0], section=lunch_sec, relationship=self.enrolled_rt
        )

        # Create a new generator with empty timeslots
        new_lcg = LunchConstraintGenerator(self.program, [])
        failed_secs, failed_subjs = new_lcg.clear_existing_constraints()

        self.assertEqual(len(failed_secs), 1)
        self.assertEqual(failed_secs[0].id, lunch_sec.id)
        # ClassSubject is also preserved because its section could not be deleted
        self.assertTrue(ClassSubject.objects.filter(id=lunch_sec.parent_class.id).exists())


class AdminClassDeleteSectionTest(ProgramFrameworkTest):
    def setUp(self):
        modules = [
            ProgramModule.objects.get(handler='AdminCore'),
            ProgramModule.objects.get(handler='AdminClass'),
        ]
        super().setUp(
            modules=modules,
            num_teachers=1,
            num_students=2,
            classes_per_teacher=1,
            sections_per_class=2,
        )
        self.add_user_profiles()
        self.adminUser, _ = ESPUser.objects.get_or_create(username='admin_class')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.client.login(username='admin_class', password='password')
        self.enrolled_rt, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', category='student'
        )

    def test_deletesection_occupied_fails_with_error_message(self):
        cls = self.program.classes().first()
        sec = cls.sections.first()
        StudentRegistration.objects.create(
            user=self.students[0], section=sec, relationship=self.enrolled_rt
        )
        url = f"/manage/{self.program.url}/deletesection/{cls.id}?sec_id={sec.id}"
        response = self.client.post(url, {'sure': 'True'})
        self.assertEqual(response.status_code, 302)
        # Section should still exist
        self.assertTrue(ClassSection.objects.filter(id=sec.id).exists())
        # Message should be present
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("Could not delete section" in m for m in messages))
        self.assertTrue(any("1 student is registered for it" in m for m in messages))

    def test_deletesection_unoccupied_succeeds(self):
        cls = self.program.classes().first()
        sec = cls.sections.first()
        sec_id = sec.id
        url = f"/manage/{self.program.url}/deletesection/{cls.id}?sec_id={sec_id}"
        response = self.client.post(url, {'sure': 'True'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClassSection.objects.filter(id=sec_id).exists())



"""
Unit tests for VolunteerManage (volunteermanage.py).
"""
from datetime import date, datetime, timedelta
from unittest.mock import patch

from esp.cal.models import Event, EventType
from esp.program.models import Program, VolunteerOffer, VolunteerRequest
from esp.program.modules.handlers.volunteermanage import VolunteerManage
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest


class VolunteerManageTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 1, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.module = self.get_module_obj('VolunteerManage')
        self.vol_type = EventType.get_from_desc('Volunteer')

    def _url(self):
        return self.get_module_url('manage', 'volunteering')

    def _make_request(self, program=None, description='Registration Desk', hours_offset=0):
        program = program or self.program
        start = datetime(2222, 7, 7, 9, 0) + timedelta(hours=hours_offset)
        end = start + timedelta(hours=2)
        ts = Event.objects.create(
            program=program,
            start=start,
            end=end,
            event_type=self.vol_type,
            short_description=description,
            description=description,
        )
        return VolunteerRequest.objects.create(
            program=program, timeslot=ts, num_volunteers=3
        )

    def test_landing_page_renders_for_admin(self):
        self.login_as('admin')
        response = self.assert_view_ok(self._url())
        self.assertIn('shift_form', response.context)
        self.assertIn('requests', response.context)
        self.assertIn('num_vol', response.context)

    def test_student_cannot_access(self):
        self.login_as('student')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    def test_create_volunteer_request(self):
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'vr_id': '',
            'start_time': '07/07/2222 09:00',
            'end_time': '07/07/2222 11:00',
            'num_volunteers': '5',
            'description': 'Security',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            VolunteerRequest.objects.filter(
                program=self.program, timeslot__description='Security'
            ).exists()
        )
        vr = VolunteerRequest.objects.get(
            program=self.program, timeslot__description='Security'
        )
        self.assertEqual(vr.num_volunteers, 5)

    def test_edit_volunteer_request(self):
        vr = self._make_request()
        self.login_as('admin')
        response = self.client.get(self._url() + '?op=edit&id=%s' % vr.id)
        self.assertEqual(response.status_code, 200)
        form = response.context['shift_form']
        self.assertEqual(form.initial.get('vr_id'), vr.id)

        response = self.client.post(self._url(), {
            'vr_id': str(vr.id),
            'start_time': '07/07/2222 10:00',
            'end_time': '07/07/2222 12:00',
            'num_volunteers': '8',
            'description': 'Updated Desk',
        })
        self.assertEqual(response.status_code, 200)
        vr.refresh_from_db()
        self.assertEqual(vr.num_volunteers, 8)
        self.assertEqual(vr.timeslot.description, 'Updated Desk')

    def test_delete_volunteer_request(self):
        vr = self._make_request()
        vr_id = vr.id
        self.login_as('admin')
        response = self.client.get(self._url() + '?op=delete&id=%s' % vr_id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(VolunteerRequest.objects.filter(id=vr_id).exists())

    def test_csv_export(self):
        vr = self._make_request()
        VolunteerOffer.objects.create(
            request=vr,
            name='Vol One',
            email='vol@example.com',
            phone='+12015550100',
            comments='Ready',
            confirmed=True,
        )
        self.login_as('admin')
        response = self.client.get(self._url() + '/csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('Activity', content)
        self.assertIn('Registration Desk', content)
        self.assertIn('Vol One', content)
        self.assertIn('vol@example.com', content)

    def test_get_admin_search_entry(self):
        entry = VolunteerManage.get_admin_search_entry(
            self.program, 'manage', 'volunteering', self.module
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.title, 'Manage Volunteers')

    def test_get_admin_search_entry_unknown_view(self):
        entry = VolunteerManage.get_admin_search_entry(
            self.program, 'manage', 'other', self.module
        )
        self.assertIsNone(entry)

    def test_check_volunteer_redirects_without_user(self):
        self.login_as('admin')
        response = self.client.get(self.get_module_url('manage', 'check_volunteer'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self._url())

    def _past_program_with_request(self, description='Past Desk'):
        past = Program.objects.create(
            url='PastProgram/1901_Spring',
            name='PastProgram Spring 1901',
            grade_min=7,
            grade_max=12,
        )
        return past, self._make_request(program=past, description=description)

    def test_import_preview_renders_confirmation(self):
        past, past_vr = self._past_program_with_request()
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'import': '1',
            'program': str(past.id),
            'start_date': '07/08/2222',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('new_requests', response.context)
        self.assertGreaterEqual(len(response.context['new_requests']), 1)
        self.assertEqual(response.context['new_requests'][0].old_id, past_vr.id)
        self.assertFalse(
            VolunteerRequest.objects.filter(
                program=self.program, timeslot__description='Past Desk'
            ).exists()
        )

    def test_import_save_creates_selected_requests(self):
        past, past_vr = self._past_program_with_request()
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'import_confirm': 'yes',
            'program': str(past.id),
            'start_date': '07/08/2222',
            'to_import': [str(past_vr.id)],
        })
        self.assertEqual(response.status_code, 200)
        new_vr = VolunteerRequest.objects.get(
            program=self.program, timeslot__description='Past Desk'
        )
        self.assertEqual(new_vr.num_volunteers, past_vr.num_volunteers)
        self.assertTrue(
            Event.objects.filter(
                program=self.program, description='Past Desk'
            ).exists()
        )

    def test_import_invalid_form_sets_import_error(self):
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'import': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['import_request_form'].is_valid())

        request = type('Req', (), {
            'POST': {
                'import': '1',
                'program': str(self.program.id),
                'start_date': '07/08/2222',
            },
            'method': 'POST',
            'user': self.admins[0],
        })()
        with patch(
            'esp.program.modules.handlers.volunteermanage.VolunteerImportForm'
        ) as MockForm:
            inst = MockForm.return_value
            inst.is_valid.return_value = True
            inst.cleaned_data = {
                'program': self.program,
                'start_date': date(2222, 7, 8),
            }
            _, context = self.module.volunteer_import(
                request, 'manage', 'one', 'two', None, None, self.program
            )
        self.assertIn('import_error', context)

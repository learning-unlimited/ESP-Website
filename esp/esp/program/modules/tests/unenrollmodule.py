from datetime import datetime
import json
import random

from esp.program.models import ClassSection, RegistrationType, StudentRegistration
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tests.factories import make_class, make_program
from esp.users.models import ESPUser, Record, RecordType

class UnenrollModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_students': 30
        })
        super().setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # mark some of the students as checked in
        for student in random.sample(self.students, 10):
            rt = RecordType.objects.get(name='attended')
            Record.objects.create(
                event=rt, program=self.program, user=student)

        self.timeslots = self.program.getTimeSlots()

        pm = ProgramModule.objects.get(handler='UnenrollModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        self.admin, created = ESPUser.objects.get_or_create(username='admin')
        self.admin.set_password('password')
        self.admin.makeAdmin()

    def test_page(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/onsite/' + self.program.url + '/unenroll_students')
        self.assertContains(r, "Select Students to Unenroll")
        for timeslot in self.program.getTimeSlotList():
            self.assertContains(r, timeslot.short_description)

    def test_json_view(self):
        self.client.login(username='admin', password='password')
        response = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(str(response.content, encoding='UTF-8'))

        self.assertGreaterEqual(len(data['student_timeslots']), 20)
        self.assertGreater(len(data['section_timeslots']), 0)
        self.assertGreater(len(data['enrollments']), 0)

        for student_id, ts_id in data['student_timeslots'].items():
            self.assertTrue(self.timeslots.filter(id=ts_id).exists())
            self.assertTrue(StudentRegistration.valid_objects().filter(
                user=student_id, section__meeting_times=ts_id).exists())
            self.assertFalse(Record.objects.filter(
                event__name='attended', program=self.program,
                user=student_id).exists())

        for section_id, ts_id in data['section_timeslots'].items():
            self.assertTrue(self.timeslots.filter(id=ts_id).exists())
            sec = ClassSection.objects.get(id=section_id)
            self.assertTrue(sec.meeting_times.filter(id=ts_id).exists())
            self.assertTrue(StudentRegistration.valid_objects().filter(
                section=section_id).exists())

        for sr_id, (user_id, section_id) in data['enrollments'].items():
            sr = StudentRegistration.objects.get(id=sr_id)
            self.assertEqual(sr.user_id, user_id)
            self.assertEqual(sr.section_id, section_id)
            self.assertIn(str(user_id), data['student_timeslots'])
            self.assertIn(str(section_id), data['section_timeslots'])

    def test_submit(self):
        self.client.login(username='admin', password='password')
        response = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(str(response.content, encoding='UTF-8'))
        enrollment_ids = list(data['enrollments'].keys())

        r = self.client.post('/onsite/' + self.program.url + '/unenroll_students', {'selected_enrollments': ','.join(enrollment_ids)})
        self.assertContains(r, 'Expired %d student registrations' % len(enrollment_ids))
        self.assertContains(r, ','.join(enrollment_ids))

        enrollments = StudentRegistration.objects.filter(id__in=enrollment_ids)
        self.assertFalse(enrollments.filter(StudentRegistration.is_valid_qobject()).exists())

        enrollments.update(end_date=None)

    def test_empty_selection(self):
        """Verify that submitting an empty selection returns HTTP 200 with an error and does not mutate registrations."""
        self.client.login(username='admin', password='password')
        regs_before = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertGreater(len(regs_before), 0)

        r = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': ''}
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Select Students to Unenroll")
        self.assertContains(r, "No enrollments selected.")

        regs_after = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertEqual(regs_before, regs_after)

    def test_missing_selection_field(self):
        """Verify that omitting the selected_enrollments field returns HTTP 200 with an error and preserves registrations."""
        self.client.login(username='admin', password='password')
        regs_before = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertGreater(len(regs_before), 0)

        r = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {}
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Select Students to Unenroll")
        self.assertContains(r, "No enrollments selected.")

        regs_after = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertEqual(regs_before, regs_after)

    def test_whitespace_only_selection(self):
        """Verify that whitespace-only selected_enrollments is treated as empty without altering registrations."""
        self.client.login(username='admin', password='password')
        regs_before = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertGreater(len(regs_before), 0)

        r = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': '   '}
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Select Students to Unenroll")
        self.assertContains(r, "No enrollments selected.")

        regs_after = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertEqual(regs_before, regs_after)

    def test_valid_submission_after_empty_selection(self):
        """Verify that valid unenrollment can be submitted successfully following an empty selection attempt."""
        self.client.login(username='admin', password='password')
        r_empty = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': ''}
        )
        self.assertEqual(r_empty.status_code, 200)
        self.assertContains(r_empty, "No enrollments selected.")

        response = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(str(response.content, encoding='UTF-8'))
        enrollment_ids = list(data['enrollments'].keys())

        r_valid = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': ','.join(enrollment_ids)}
        )
        self.assertContains(r_valid, 'Expired %d student registrations' % len(enrollment_ids))
        self.assertContains(r_valid, ','.join(enrollment_ids))

        enrollments = StudentRegistration.objects.filter(id__in=enrollment_ids)
        self.assertFalse(enrollments.filter(StudentRegistration.is_valid_qobject()).exists())
        enrollments.update(end_date=None)

    def test_undo_empty_selection(self):
        """Verify that submitting undo with an empty selection returns HTTP 200 with an error and leaves registrations unchanged."""
        self.client.login(username='admin', password='password')
        regs_before = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertGreater(len(regs_before), 0)

        r = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': '', 'undo': ''}
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Select Students to Unenroll")
        self.assertContains(r, "No enrollments selected.")

        regs_after = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertEqual(regs_before, regs_after)

    def test_comma_only_selection(self):
        """Verify that comma/whitespace-only selected_enrollments is treated as empty without altering registrations."""
        self.client.login(username='admin', password='password')
        regs_before = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))

        for raw in (',', ',,, ', ' , , '):
            r = self.client.post(
                '/onsite/' + self.program.url + '/unenroll_students',
                {'selected_enrollments': raw}
            )
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "Select Students to Unenroll")
            self.assertContains(r, "No enrollments selected.")

        regs_after = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertEqual(regs_before, regs_after)

    def test_trailing_comma_and_whitespace_sanitized(self):
        """Verify that trailing commas, empty tokens, and whitespace around valid IDs succeed for unenroll and undo."""
        self.client.login(username='admin', password='password')
        response = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(str(response.content, encoding='UTF-8'))
        enrollment_ids = list(data['enrollments'].keys())[:2]
        self.assertEqual(len(enrollment_ids), 2)

        payload = f' , {enrollment_ids[0]} , {enrollment_ids[1]}, '
        r = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': payload}
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Expired 2 student registrations')
        self.assertContains(r, f'value="{",".join(enrollment_ids)}"')

        enrollments = StudentRegistration.objects.filter(id__in=enrollment_ids)
        self.assertFalse(enrollments.filter(StudentRegistration.is_valid_qobject()).exists())

        r_undo = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': payload, 'undo': ''}
        )
        self.assertEqual(r_undo.status_code, 200)
        self.assertContains(r_undo, 'Unexpired 2 student registrations')
        self.assertEqual(
            enrollments.filter(StudentRegistration.is_valid_qobject()).count(),
            2
        )

    def test_malformed_and_out_of_range_selection(self):
        """Verify that non-integer or out-of-range IDs return a validation error without mutating registrations."""
        self.client.login(username='admin', password='password')
        response = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(str(response.content, encoding='UTF-8'))
        valid_id = next(iter(data['enrollments'].keys()))

        regs_before = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))

        bad_inputs = [
            'abc',
            f'{valid_id},abc',
            f'{valid_id}, 1.5',
            '-1',
            '0',
            '1_0',
            '99999999999999999999',
        ]
        for bad in bad_inputs:
            for extra in ({}, {'undo': ''}):
                r = self.client.post(
                    '/onsite/' + self.program.url + '/unenroll_students',
                    {'selected_enrollments': bad, **extra}
                )
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, "Select Students to Unenroll")
                self.assertContains(r, "Invalid enrollment selection.")

        regs_after = list(StudentRegistration.objects.all().values(
            'id', 'end_date', 'relationship_id', 'section_id', 'user_id'
        ))
        self.assertEqual(regs_before, regs_after)

    def test_unenroll_and_undo_scoped_to_program(self):
        """Verify that unenroll_students cannot expire or unexpire registrations from another program."""
        other_program = make_program(
            program_type='OtherProgram',
            instance_name='2223_Fall',
            instance_label='Fall 2223',
            start_time=datetime(2223, 7, 7, 7, 5),
            admins=[self.admin],
            categories=self.categories,
        )
        other_cls = make_class(
            other_program,
            self.teachers[0],
            title='Other Program Class',
            accept=True,
        )
        other_section = other_cls.get_sections().first()
        enrolled_rt = RegistrationType.objects.get(name='Enrolled')
        other_reg = StudentRegistration.objects.create(
            user=self.students[0],
            section=other_section,
            relationship=enrolled_rt,
        )

        own_reg = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=self.program,
            relationship=enrolled_rt,
        ).first()
        self.assertIsNotNone(own_reg)

        self.client.login(username='admin', password='password')

        # Foreign-only ID should expire 0 registrations and leave other_reg active
        r_foreign = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': str(other_reg.id)}
        )
        self.assertEqual(r_foreign.status_code, 200)
        self.assertContains(r_foreign, 'Expired 0 student registrations')
        self.assertContains(r_foreign, 'value=""')
        other_reg.refresh_from_db()
        self.assertIsNone(other_reg.end_date)

        # Mixed own + foreign IDs should only expire own_reg
        r_mixed = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': f'{own_reg.id},{other_reg.id}'}
        )
        self.assertEqual(r_mixed.status_code, 200)
        self.assertContains(r_mixed, 'Expired 1 student registrations')
        self.assertContains(r_mixed, f'value="{own_reg.id}"')
        own_reg.refresh_from_db()
        other_reg.refresh_from_db()
        self.assertIsNotNone(own_reg.end_date)
        self.assertIsNone(other_reg.end_date)

        # Undo with mixed own + foreign IDs should only unexpire own_reg
        frozen_end = datetime(2223, 1, 1, 12, 0)
        StudentRegistration.objects.filter(id=other_reg.id).update(end_date=frozen_end)
        r_undo = self.client.post(
            '/onsite/' + self.program.url + '/unenroll_students',
            {'selected_enrollments': f'{own_reg.id},{other_reg.id}', 'undo': ''}
        )
        self.assertEqual(r_undo.status_code, 200)
        self.assertContains(r_undo, 'Unexpired 1 student registrations')
        own_reg.refresh_from_db()
        other_reg.refresh_from_db()
        self.assertIsNone(own_reg.end_date)
        self.assertEqual(other_reg.end_date, frozen_end)

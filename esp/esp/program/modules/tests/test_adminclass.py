"""
Tests for AdminClass program module (adminclass.py).

Covers:
- Class status transitions (approveclass, rejectclass, proposeclass, deleteclass)
- ClassCancellationForm validation and manageclass cancel_cls action
- SectionManageForm validation and manageclass modify_sec action
- classavailability view scheduling conflict detection
"""

from esp.program.class_status import ClassStatus
from esp.program.models import ClassSection, ClassSubject
from esp.program.modules.forms.management import ClassCancellationForm
from esp.program.tests import ProgramFrameworkTest


class ClassStateTransitionTest(ProgramFrameworkTest):
    """Tests for approveclass, rejectclass, proposeclass, and deleteclass."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')
        self.cls = self.program.classes()[0]
        self.manage_url = self.program.get_manage_url()

    def test_approveclass_transitions_to_accepted(self):
        """approveclass sets ClassSubject and non-cancelled sections to ACCEPTED."""
        self.cls.propose()
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.UNREVIEWED)

        response = self.client.get(f'{self.manage_url}approveclass/{self.cls.id}')
        self.assertRedirects(
            response,
            f'{self.manage_url}manageclass/{self.cls.id}',
            fetch_redirect_response=False,
        )

        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.ACCEPTED)
        for sec in ClassSection.objects.filter(parent_class=self.cls):
            self.assertEqual(sec.status, ClassStatus.ACCEPTED)

    def test_rejectclass_transitions_to_rejected(self):
        """rejectclass sets ClassSubject and sections to REJECTED."""
        self.cls.accept()
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.ACCEPTED)

        response = self.client.get(f'{self.manage_url}rejectclass/{self.cls.id}')
        self.assertRedirects(
            response,
            f'{self.manage_url}manageclass/{self.cls.id}',
            fetch_redirect_response=False,
        )

        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.REJECTED)
        for sec in ClassSection.objects.filter(parent_class=self.cls):
            self.assertEqual(sec.status, ClassStatus.REJECTED)

    def test_proposeclass_transitions_to_unreviewed(self):
        """proposeclass sets ClassSubject and sections to UNREVIEWED."""
        self.cls.accept()
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.ACCEPTED)

        response = self.client.get(f'{self.manage_url}proposeclass/{self.cls.id}')
        self.assertRedirects(
            response,
            f'{self.manage_url}manageclass/{self.cls.id}',
            fetch_redirect_response=False,
        )

        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.UNREVIEWED)
        for sec in ClassSection.objects.filter(parent_class=self.cls):
            self.assertEqual(sec.status, ClassStatus.UNREVIEWED)

    def test_deleteclass_removes_class_and_sections(self):
        """deleteclass removes the ClassSubject and its sections from the database."""
        cls_id = self.cls.id
        self.assertTrue(ClassSubject.objects.filter(pk=cls_id).exists())
        self.assertTrue(ClassSection.objects.filter(parent_class_id=cls_id).exists())

        response = self.client.get(f'{self.manage_url}deleteclass/{cls_id}')
        self.assertRedirects(
            response,
            f'{self.manage_url}dashboard',
            fetch_redirect_response=False,
        )

        self.assertFalse(ClassSubject.objects.filter(pk=cls_id).exists())
        self.assertFalse(ClassSection.objects.filter(parent_class_id=cls_id).exists())


class ClassCancellationFormTest(ProgramFrameworkTest):
    """Tests for ClassCancellationForm validation and manageclass actions."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')
        self.cls = self.program.classes()[0]

        # Ensure class has a scheduled section so hasScheduledSections() is True
        self.sec = self.cls.sections.first()
        self.timeslot = self.program.getTimeSlots().first()
        self.sec.meeting_times.clear()
        self.sec.meeting_times.add(self.timeslot)

        self.manage_url = f'{self.program.get_manage_url()}manageclass/{self.cls.id}'

    def test_cancellation_form_valid_with_acknowledgement(self):
        """ClassCancellationForm is valid when required acknowledgement is True."""
        form = ClassCancellationForm(
            subject=self.cls,
            data={
                'target': self.cls.id,
                'explanation': 'Cancelled for testing',
                'acknowledgement': True,
                'unschedule': False,
                'email_lottery_students': False,
                'text_students': False,
                'email_teachers': False,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_cancellation_form_invalid_without_acknowledgement(self):
        """ClassCancellationForm is invalid when acknowledgement is omitted."""
        form = ClassCancellationForm(
            subject=self.cls,
            data={
                'target': self.cls.id,
                'explanation': 'Cancelled for testing',
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('acknowledgement', form.errors)

    def test_cancel_cls_action_requires_acknowledgement(self):
        """manageclass with action=cancel_cls without acknowledgement leaves class uncancelled."""
        initial_status = self.cls.status
        response = self.client.post(
            f'{self.manage_url}?action=cancel_cls',
            {
                'target': self.cls.id,
                'explanation': 'Testing cancellation failure',
                # acknowledgement omitted to simulate unchecked checkbox
            },
        )
        # Form validation failure re-renders the manageclass page (200 OK)
        self.assertEqual(response.status_code, 200)

        self.cls.refresh_from_db()
        self.assertEqual(self.cls.status, initial_status)
        self.assertNotEqual(self.cls.status, ClassStatus.CANCELLED)

    def test_cancel_cls_action_valid_submission_cancels_class(self):
        """manageclass with action=cancel_cls and valid data cancels class and sections."""
        response = self.client.post(
            f'{self.manage_url}?action=cancel_cls',
            {
                'target': self.cls.id,
                'explanation': 'Reason for cancellation',
                'acknowledgement': 'on',
                'unschedule': '',
                'email_lottery_students': '',
                'text_students': '',
                'email_teachers': '',
            },
        )
        # Successful cancellation redirects to reload the manageclass view
        self.assertIn(response.status_code, [200, 302])

        self.cls.refresh_from_db()
        self.assertEqual(self.cls.status, ClassStatus.CANCELLED)
        for sec in self.cls.sections.all():
            self.assertEqual(sec.status, ClassStatus.CANCELLED)

    def test_modify_sec_action_updates_section_data(self):
        """manageclass with action=modify_sec and valid data updates section capacity."""
        prefix = f'sec{self.sec.index()}'
        new_capacity = 45
        post_data = {
            f'{prefix}-secid': self.sec.id,
            f'{prefix}-status': ClassStatus.ACCEPTED,
            f'{prefix}-reg_status': '',
            f'{prefix}-times': [self.timeslot.id],
            f'{prefix}-room': [],
            f'{prefix}-resources': [],
            f'{prefix}-class_size': new_capacity,
        }

        response = self.client.post(f'{self.manage_url}?action=modify_sec', post_data)
        self.assertIn(response.status_code, [200, 302])

        self.sec.refresh_from_db()
        self.assertEqual(self.sec.max_class_capacity, new_capacity)

    def test_modify_sec_action_invalid_input_does_not_update_section(self):
        """manageclass with action=modify_sec and invalid data leaves section unchanged."""
        original_capacity = self.sec.max_class_capacity
        prefix = f'sec{self.sec.index()}'
        post_data = {
            f'{prefix}-secid': self.sec.id,
            f'{prefix}-status': 'invalid_status_choice',
            f'{prefix}-class_size': 'not-an-integer',
        }

        response = self.client.post(f'{self.manage_url}?action=modify_sec', post_data)
        self.assertEqual(response.status_code, 200)

        self.sec.refresh_from_db()
        self.assertEqual(self.sec.max_class_capacity, original_capacity)


class ClassAvailabilityConflictTest(ProgramFrameworkTest):
    """Tests for classavailability view and scheduling conflict detection."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')
        self.cls = self.program.classes()[0]
        self.teacher = self.cls.get_teachers()[0]

        # Ensure deterministically scheduled meeting time
        self.sec = self.cls.sections.first()
        self.timeslot = self.program.getTimeSlots().first()
        self.sec.meeting_times.clear()
        self.sec.meeting_times.add(self.timeslot)

        self.url = f'{self.program.get_manage_url()}classavailability/{self.cls.id}'

    def test_no_conflict_when_teacher_is_available(self):
        """conflict_found is False when teacher is available at class meeting times."""
        for ts in self.program.getTimeSlots():
            self.teacher.addAvailableTime(self.program, ts)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['conflict_found'])

    def test_conflict_found_when_teacher_is_unavailable_at_scheduled_time(self):
        """conflict_found is True when teacher is unavailable at a scheduled class meeting time."""
        # Clear all available times so teacher is unavailable during the meeting time
        self.teacher.clearAvailableTimes(self.program)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['conflict_found'])

        # Verify teacher is tracked under unavail_teachers for the scheduled timeslot
        all_slot_entries = [
            item for group in response.context['groups'] for item in group
        ]
        matching_entry = next(
            (item for item in all_slot_entries if item['slot'].id == self.timeslot.id),
            None,
        )
        self.assertIsNotNone(matching_entry)
        self.assertIn(self.teacher, matching_entry['unavail_teachers'])

    def test_classavailability_context_keys(self):
        """classavailability view populates all expected context keys."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for key in ('conflict_found', 'groups', 'class', 'unscheduled', 'program', 'is_overbooked', 'num_groups'):
            self.assertIn(key, response.context)
        self.assertEqual(response.context['class'], self.cls)
        self.assertEqual(response.context['program'], self.program)

from unittest.mock import patch

from esp.program.tests import ProgramFrameworkTest
from esp.program.class_status import ClassStatus
from esp.program.models import ClassSubject
from esp.program.modules.forms.management import ClassCancellationForm


class ClassStateTransitionTest(ProgramFrameworkTest):
    """Tests for approveclass, rejectclass, proposeclass, deleteclass."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')
        self.cls = self.program.classes()[0]
        self.manage_url = '/manage/%s/' % self.program.url

    def test_approveclass(self):
        self.cls.propose()
        response = self.client.get(self.manage_url + 'approveclass/%s' % self.cls.id)
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.ACCEPTED)

    def test_rejectclass(self):
        self.cls.propose()
        response = self.client.get(self.manage_url + 'rejectclass/%s' % self.cls.id)
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.REJECTED)

    def test_proposeclass(self):
        self.cls.accept()
        response = self.client.get(self.manage_url + 'proposeclass/%s' % self.cls.id)
        self.assertIn(response.status_code, [200, 302])
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.UNREVIEWED)

    def test_deleteclass(self):
        cls_id = self.cls.id
        response = self.client.get(self.manage_url + 'deleteclass/%s' % cls_id)
        self.assertIn(response.status_code, [200, 302])
        self.assertFalse(ClassSubject.objects.filter(pk=cls_id).exists())

    def test_approveclass_redirect_param(self):
        """redirect GET param is followed after approve."""
        self.cls.propose()
        redirect_to = self.manage_url + 'dashboard'
        response = self.client.get(
            self.manage_url + 'approveclass/%s?redirect=%s' % (self.cls.id, redirect_to)
        )
        self.assertRedirects(response, redirect_to, fetch_redirect_response=False)

    def test_rejectclass_redirect_param(self):
        """redirect GET param is followed after reject."""
        self.cls.propose()
        redirect_to = self.manage_url + 'dashboard'
        response = self.client.get(
            self.manage_url + 'rejectclass/%s?redirect=%s' % (self.cls.id, redirect_to)
        )
        self.assertRedirects(response, redirect_to, fetch_redirect_response=False)


class ClassCancellationFormTest(ProgramFrameworkTest):
    """Tests for ClassCancellationForm validation and manageclass cancel_cls/modify_sec actions."""

    def setUp(self):
        super().setUp()
        self.schedule_randomly()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')
        # Pick a scheduled, non-cancelled class
        self.cls = next(
            c for c in self.program.classes()
            if not c.isCancelled() and c.hasScheduledSections()
        )
        self.manage_url = '/manage/%s/manageclass/%s' % (self.program.url, self.cls.id)

    def test_cancel_cls_requires_acknowledgement(self):
        """Submitting cancel_cls without acknowledgement leaves class unchanged."""
        self.client.post(
            self.manage_url + '?action=cancel_cls',
            {'target': self.cls.id, 'explanation': 'test', 'acknowledgement': ''},
        )
        self.assertEqual(ClassSubject.objects.get(pk=self.cls.id).status, ClassStatus.ACCEPTED)

    def test_cancel_cls_valid_cancels_class(self):
        """Valid cancel_cls POST with acknowledgement triggers cancel()."""
        with patch.object(ClassSubject, 'cancel') as mock_cancel:
            response = self.client.post(
                self.manage_url + '?action=cancel_cls',
                {
                    'target': self.cls.id,
                    'explanation': 'Cancelled for testing',
                    'acknowledgement': 'on',
                    'unschedule': '',
                    'email_lottery_students': '',
                    'text_students': '',
                    'email_teachers': '',
                },
            )
        mock_cancel.assert_called_once()
        self.assertIn(response.status_code, [200, 302])

    def test_cancellation_form_valid_with_required_fields(self):
        """ClassCancellationForm is valid when acknowledgement is True."""
        form = ClassCancellationForm(
            subject=self.cls,
            data={
                'target': self.cls.id,
                'explanation': 'test reason',
                'acknowledgement': True,
                'unschedule': False,
                'email_lottery_students': False,
                'text_students': False,
                'email_teachers': False,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_cancellation_form_invalid_without_acknowledgement(self):
        """ClassCancellationForm is invalid when acknowledgement is missing."""
        form = ClassCancellationForm(
            subject=self.cls,
            data={
                'target': self.cls.id,
                'explanation': 'test reason',
                'acknowledgement': False,
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('acknowledgement', form.errors)

    def test_modify_sec_action_processes_section_form(self):
        """modify_sec POST with valid section data returns 200 or redirect."""
        sec = self.cls.sections.all()[0]
        prefix = 'sec%d' % sec.index()
        response = self.client.post(
            self.manage_url + '?action=modify_sec',
            {
                '%s-secid' % prefix: sec.id,
                '%s-status' % prefix: ClassStatus.ACCEPTED,
                '%s-reg_status' % prefix: '',
                '%s-times' % prefix: [],
                '%s-room' % prefix: [],
                '%s-resources' % prefix: [],
                '%s-class_size' % prefix: '',
            },
        )
        self.assertIn(response.status_code, [200, 302])


class ClassAvailabilityConflictTest(ProgramFrameworkTest):
    """Tests for classavailability view and the conflict_found context variable."""

    def setUp(self):
        super().setUp()
        self.schedule_randomly()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')

    def test_no_conflict_when_teacher_available(self):
        """conflict_found is False when teacher is available for all timeslots."""
        cls = self.program.classes()[0]
        teacher = cls.get_teachers()[0]
        for ts in self.program.getTimeSlots():
            teacher.addAvailableTime(self.program, ts)

        response = self.client.get('/manage/%s/classavailability/%s' % (self.program.url, cls.id))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['conflict_found'])

    def test_conflict_found_when_teacher_unavailable_at_scheduled_time(self):
        """conflict_found is True when teacher has no availability at a scheduled timeslot."""
        cls = next(
            (c for c in self.program.classes() if c.hasScheduledSections()),
            None,
        )
        if cls is None:
            self.skipTest('No scheduled classes available for conflict test')

        teacher = cls.get_teachers()[0]
        # Remove all availability — teacher is now unavailable at every scheduled time
        teacher.clearAvailableTimes(self.program)

        response = self.client.get('/manage/%s/classavailability/%s' % (self.program.url, cls.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['conflict_found'])

    def test_classavailability_context_keys(self):
        """classavailability view always populates the expected context keys."""
        cls = self.program.classes()[0]
        response = self.client.get('/manage/%s/classavailability/%s' % (self.program.url, cls.id))
        self.assertEqual(response.status_code, 200)
        for key in ('conflict_found', 'groups', 'class', 'unscheduled', 'program'):
            self.assertIn(key, response.context)

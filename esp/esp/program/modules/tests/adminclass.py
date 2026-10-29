import json
from urllib.parse import urlencode

from django.core import mail

from esp.program.class_status import ClassStatus
from esp.program.models import ClassSection, ClassSubject
from esp.program.modules.forms.management import ClassCancellationForm
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class CancelClassTest(ProgramFrameworkTest):
    def setUp(self):
        # Set up the program framework and randomly schedule classes
        super().setUp()
        self.schedule_randomly()

        # Find a class to be cancelled
        self.cls = self.teachers[0].getTaughtClasses()[0]
        # Ensure class has a scheduled section so hasScheduledSections() is True
        self.sec = self.cls.sections.first()
        self.timeslot = self.program.getTimeSlots().first()
        self.sec.meeting_times.clear()
        self.sec.meeting_times.add(self.timeslot)

        # Put a student in it
        self.student = self.students[0]
        self.student.email = "testing@localhost"
        self.student.save()
        self.sec.preregister_student(self.student, True, True)

        # Create an admin account
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.adminUser.save()

        self.manage_url = f'{self.program.get_manage_url()}manageclass/{self.cls.id}'

    def testCancelClass(self):
        # Login with the admin account
        self.client.login(username='admin', password='password')

        # Cancel the class with teacher notification enabled
        cancelMsg = 'Testing cancel class'
        cancel_url = f'{self.manage_url}?action=cancel_cls'
        response = self.client.post(
            cancel_url,
            {
                'acknowledgement': 'on',
                'explanation': cancelMsg,
                'target': self.cls.id,
                'email_teachers': 'on',
            },
        )
        self.assertRedirects(response, cancel_url, fetch_redirect_response=False)

        # Update the class
        self.cls = ClassSubject.objects.get(pk=self.cls.id)

        # Check that the class was changed to cancelled
        self.assertEqual(self.cls.status, ClassStatus.CANCELLED)
        # Check that the sections were cancelled
        for sec in self.cls.sections.all():
            self.assertEqual(sec.status, ClassStatus.CANCELLED)
            self.assertEqual(sec.cancellation_reason, cancelMsg)

        # Test that emails were sent (director, student, and teacher)
        directorEmail = None
        studentEmail = None
        teacherEmail = None
        for m in mail.outbox:
            for addr in m.to:
                if self.program.director_email in addr:
                    directorEmail = m
                    break
                elif self.student.email in addr:
                    studentEmail = m
                    break
                elif self.teachers[0].email in addr:
                    teacherEmail = m
                    break

        self.assertTrue(directorEmail is not None and cancelMsg in directorEmail.body)
        self.assertTrue(studentEmail is not None and cancelMsg in studentEmail.body)
        self.assertTrue(teacherEmail is not None and cancelMsg in teacherEmail.body)

        # Check that classes show up in the cancelled classes printable
        r = self.client.get("/manage/" + self.program.url + "/classesbytime?cancelled")
        self.assertContains(r, self.cls.emailcode(), status_code=200)

    def testCancelSectionWithNoneExplanationPersistsNone(self):
        sec = self.cls.sections.all()[0]
        sec.cancel(email_students=False, include_lottery_students=False, text_students=False,
                   email_teachers=False, explanation=None, unschedule=False)
        sec.refresh_from_db()
        self.assertEqual(sec.status, ClassStatus.CANCELLED)
        self.assertIsNone(sec.cancellation_reason)

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
        self.client.login(username='admin', password='password')
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

    # Regression: fix for GET/POST boolean guard in admin teacherlookup
    def test_teacherlookup_post_with_name_returns_json(self):
        """POST with 'name' absent from GET must return JSON, not redirect."""
        self.client.login(username='admin', password='password')
        url = '%steacherlookup' % self.program.get_manage_url()
        response = self.client.post(url, {'name': 'teacher'})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(json.loads(response.content), list)

    def test_teacherlookup_no_name_redirects(self):
        """Request without 'name' in GET or POST must redirect via goToCore."""
        self.client.login(username='admin', password='password')
        url = '%steacherlookup' % self.program.get_manage_url()
        self.assertEqual(self.client.get(url).status_code, 302)


class SafeRedirectTest(ProgramFrameworkTest):
    """Tests that approveclass/rejectclass/proposeclass reject off-site 'redirect' values."""

    def setUp(self):
        super().setUp()
        self.schedule_randomly()
        self.cls = self.teachers[0].getTaughtClasses()[0]

        self.adminUser, created = ESPUser.objects.get_or_create(username='admin')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.adminUser.save()
        self.client.login(username='admin', password='password')

        self.fallback_url = '%smanageclass/%s' % (self.program.get_manage_url(), self.cls.id)

    def _action_url(self, action, redirect=None):
        url = '%s%s/%s' % (self.program.get_manage_url(), action, self.cls.id)
        if redirect is not None:
            url += '?' + urlencode({'redirect': redirect})
        return url

    def _status(self):
        return ClassSubject.objects.get(pk=self.cls.id).status

    def test_external_redirect_blocked_approveclass(self):
        """An off-site redirect is dropped, but the class is still approved."""
        self.cls.propose()
        response = self.client.get(self._action_url('approveclass', 'https://evil.com'))
        self.assertRedirects(response, self.fallback_url, fetch_redirect_response=False)
        self.assertEqual(self._status(), ClassStatus.ACCEPTED)

    def test_external_redirect_blocked_rejectclass(self):
        """An off-site redirect is dropped, but the class is still rejected."""
        response = self.client.get(self._action_url('rejectclass', 'https://evil.com'))
        self.assertRedirects(response, self.fallback_url, fetch_redirect_response=False)
        self.assertEqual(self._status(), ClassStatus.REJECTED)

    def test_external_redirect_blocked_proposeclass(self):
        """An off-site redirect is dropped, but the class is still unreviewed."""
        response = self.client.get(self._action_url('proposeclass', 'https://evil.com'))
        self.assertRedirects(response, self.fallback_url, fetch_redirect_response=False)
        self.assertEqual(self._status(), ClassStatus.UNREVIEWED)

    def test_protocol_relative_redirect_blocked(self):
        """Protocol-relative URLs (//evil.com) name another host, so they are dropped."""
        response = self.client.get(self._action_url('approveclass', '//evil.com'))
        self.assertRedirects(response, self.fallback_url, fetch_redirect_response=False)

    def test_backslash_redirect_blocked(self):
        r"""Browsers read the backslash in \/evil.com as a slash, so it is dropped too."""
        response = self.client.get(self._action_url('approveclass', '\\/evil.com'))
        self.assertRedirects(response, self.fallback_url, fetch_redirect_response=False)

    def test_internal_path_redirect_allowed(self):
        """A relative path -- what the manage templates actually send -- is honored."""
        internal_url = '%sdashboard' % self.program.get_manage_url()
        response = self.client.get(self._action_url('approveclass', internal_url))
        self.assertRedirects(response, internal_url, fetch_redirect_response=False)

    def test_same_host_absolute_redirect_allowed(self):
        """An absolute URL on this host is honored."""
        internal_url = 'http://testserver%sdashboard' % self.program.get_manage_url()
        response = self.client.get(self._action_url('approveclass', internal_url))
        self.assertRedirects(response, internal_url, fetch_redirect_response=False)

    def test_no_redirect_param_uses_fallback(self):
        """With no redirect parameter at all, the manageclass URL is used."""
        response = self.client.get(self._action_url('approveclass'))
        self.assertRedirects(response, self.fallback_url, fetch_redirect_response=False)


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


class SectionManagementTest(ProgramFrameworkTest):
    """Tests for SectionManageForm validation and manageclass modify_sec action."""

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
        self.assertRedirects(
            response,
            f'{self.manage_url}?action=modify_sec',
            fetch_redirect_response=False,
        )

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


class DeleteSectionTest(ProgramFrameworkTest):
    """Tests for the deletesection confirm/delete/cancel flow."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.client.login(username=self.admin.username, password='password')
        self.cls, self.other_cls = self.program.classes()[:2]
        self.sec = self.cls.sections.first()
        self.other_sec = self.other_cls.sections.first()

        self.url = f'{self.program.get_manage_url()}deletesection/{self.cls.id}'
        self.manage_url = f'{self.program.get_manage_url()}manageclass/{self.cls.id}'

    def _exists(self, sec):
        return ClassSection.objects.filter(id=sec.id).exists()

    def test_get_renders_confirmation(self):
        response = self.client.get(self.url, {'sec_id': self.sec.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sec'], self.sec)
        self.assertTrue(self._exists(self.sec))

    def test_confirm_with_sec_id_in_post_body_deletes(self):
        response = self.client.post(self.url, {'sec_id': self.sec.id, 'sure': 'True'})
        self.assertRedirects(response, self.manage_url, fetch_redirect_response=False)
        self.assertFalse(self._exists(self.sec))

    def test_confirm_with_sec_id_in_query_string_deletes(self):
        """Forms rendered before this fix put sec_id in the action URL."""
        response = self.client.post(f'{self.url}?sec_id={self.sec.id}', {'sure': 'True'})
        self.assertRedirects(response, self.manage_url, fetch_redirect_response=False)
        self.assertFalse(self._exists(self.sec))

    def test_cancel_redirects_without_deleting(self):
        response = self.client.post(self.url, {'sec_id': self.sec.id, 'sure': 'False'})
        self.assertRedirects(response, self.manage_url, fetch_redirect_response=False)
        self.assertTrue(self._exists(self.sec))

    def test_section_from_other_class_rejected(self):
        response = self.client.get(self.url, {'sec_id': self.other_sec.id})
        self.assertEqual(response.status_code, 500)
        response = self.client.post(self.url, {'sec_id': self.other_sec.id, 'sure': 'True'})
        self.assertEqual(response.status_code, 500)
        self.assertTrue(self._exists(self.other_sec))

    def test_missing_or_invalid_sec_id_rejected(self):
        self.assertEqual(self.client.get(self.url).status_code, 500)
        self.assertEqual(self.client.post(self.url, {'sure': 'True'}).status_code, 500)
        self.assertEqual(self.client.get(self.url, {'sec_id': 'abc'}).status_code, 500)
        self.assertTrue(self._exists(self.sec))

    def test_invalid_sec_id_not_echoed(self):
        """Error messages render unescaped, so raw input must not appear in them."""
        payload = '<script>alert(1)</script>'
        response = self.client.get(self.url, {'sec_id': payload})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(payload, response.content.decode())


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

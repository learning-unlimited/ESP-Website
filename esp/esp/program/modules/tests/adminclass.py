import json
from urllib.parse import urlencode

from esp.program.tests import ProgramFrameworkTest
from esp.program.class_status import ClassStatus
from esp.program.models import ClassSubject
from esp.users.models import ESPUser
from django.core import mail

class CancelClassTest(ProgramFrameworkTest):
    def setUp(self):
        # Set up the program framework and randomly schedule classes
        super().setUp()
        self.schedule_randomly()

        # Find a class to be cancelled
        self.cls = self.teachers[0].getTaughtClasses()[0]
        # Put a student in it
        self.student = self.students[0]
        self.student.email = "testing@localhost"
        self.student.save()
        self.cls.sections.all()[0].preregister_student(self.student, True, True)

        # Create an admin account
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.adminUser.save()

    def testCancelClass(self):
        # Login with the admin account
        self.client.login(username='admin', password='password')

        # Cancel the class
        cancelMsg = 'Testing cancel class'
        self.client.post("/manage/"+self.program.url+"/manageclass/"+str(self.cls.id)+"?action=cancel_cls", { 'acknowledgement': 'on', 'explanation': cancelMsg, 'target': self.cls.id })

        # Update the class
        self.cls = ClassSubject.objects.get(pk=self.cls.id)

        # Check that the class was changed to cancelled
        self.assertEqual(self.cls.status, ClassStatus.CANCELLED)
        # Check that the sections were cancelled
        for sec in self.cls.sections.all():
            self.assertEqual(sec.status, ClassStatus.CANCELLED)
            self.assertEqual(sec.cancellation_reason, cancelMsg)

        # Test that an email was sent
        directorEmail = None
        studentEmail = None
        for m in mail.outbox:
            for addr in m.to:
                if self.program.director_email in addr:
                    directorEmail = m
                    break
                if self.student.email in addr:
                    studentEmail = m
                    break

        self.assertTrue(directorEmail is not None and cancelMsg in directorEmail.body)
        self.assertTrue(studentEmail is not None and cancelMsg in studentEmail.body)

        # Check that classes show up in the cancelled classes printable
        r = self.client.get("/manage/"+self.program.url+"/classesbytime?cancelled")
        self.assertContains(r, self.cls.emailcode(), status_code=200)

    def testCancelSectionWithNoneExplanationPersistsNone(self):
        sec = self.cls.sections.all()[0]
        sec.cancel(email_students=False, include_lottery_students=False, text_students=False,
                   email_teachers=False, explanation=None, unschedule=False)
        sec.refresh_from_db()
        self.assertEqual(sec.status, ClassStatus.CANCELLED)
        self.assertIsNone(sec.cancellation_reason)

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

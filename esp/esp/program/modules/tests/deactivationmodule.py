from __future__ import absolute_import

from django.db.models import Q

from esp.middleware import ESPError_Log
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, PersistentQueryFilter


class DeactivationModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_students': 5,
            'num_teachers': 1,
            'num_admins': 1,
        })
        super(DeactivationModuleTest, self).setUp(*args, **kwargs)

        pm = ProgramModule.objects.get(handler='DeactivationModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        self.assertTrue(
            self.client.login(username=self.admins[0].username, password='password'),
            "Failed to log in admin user.",
        )

    def _url(self, filterid=None):
        base = '/manage/%s/deactivatefinal' % self.program.getUrlBase()
        if filterid is None:
            return base
        return '%s?filterid=%s' % (base, filterid)

    def _make_filter(self, users):
        q = Q(id__in=[user.id for user in users])
        filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filterObj.save()
        return filterObj

    def _post_deactivatefinal(self, filterid=None, data=None):
        """POST to deactivatefinal, capturing either a response or raised ESPError.

        Depending on whether ESPErrorMiddleware converts the exception into an
        HttpResponse, Django's test client may either return that response or
        re-raise ESPError_Log. Support both so these tests are environment-stable.
        """
        if data is None:
            data = {'confirm': 'on'}
        try:
            return self.client.post(self._url(filterid), data), None
        except ESPError_Log as exc:
            return None, exc

    def _assert_graceful_esp_error(self, response, exc, *substrings):
        """Assert a handled ESPError rather than an uncaught 500/traceback."""
        if exc is not None:
            message = str(exc)
            for substring in substrings:
                self.assertIn(substring, message)
            return

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        content = response.content.decode('utf-8')
        for substring in substrings:
            self.assertIn(substring, content)

    def test_deactivatefinal_valid_filterid(self):
        """A valid filterid deactivates matching users and shows the finished page."""
        targets = self.students[:2]
        for user in targets:
            user.is_active = True
            user.save()

        filterObj = self._make_filter(targets)
        response, exc = self._post_deactivatefinal(filterObj.id)

        self.assertIsNone(exc, "Unexpected ESPError for a valid filterid: %s" % exc)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FINISHED')
        for user in targets:
            user.refresh_from_db()
            self.assertFalse(user.is_active)

    def test_deactivatefinal_missing_filterid(self):
        """Missing filterid is a graceful ESPError and does not deactivate anyone."""
        target = self.students[0]
        target.is_active = True
        target.save()

        response, exc = self._post_deactivatefinal()
        self._assert_graceful_esp_error(
            response, exc, 'Filter has not been properly set',
        )

        target.refresh_from_db()
        self.assertTrue(target.is_active)

    def test_deactivatefinal_deleted_filter(self):
        """A deleted filter raises ESPError instead of an uncaught DoesNotExist."""
        targets = self.students[:2]
        for user in targets:
            user.is_active = True
            user.save()

        filterObj = self._make_filter(targets)
        filter_id = filterObj.id
        filterObj.delete()

        response, exc = self._post_deactivatefinal(filter_id)
        self._assert_graceful_esp_error(
            response, exc, 'no longer exists', 'deactivation',
        )

        for user in targets:
            user.refresh_from_db()
            self.assertTrue(user.is_active)

    def test_deactivatefinal_nonexistent_filterid(self):
        """A numeric filterid with no matching row is a graceful ESPError."""
        response, exc = self._post_deactivatefinal(99999999)
        self._assert_graceful_esp_error(
            response, exc, 'no longer exists', 'deactivation',
        )

    def test_deactivatefinal_invalid_filterid(self):
        """A non-numeric filterid is a graceful ESPError, not a ValueError/500."""
        response, exc = self._post_deactivatefinal('abc')
        self._assert_graceful_esp_error(
            response, exc, 'no longer exists', 'invalid', 'deactivation',
        )

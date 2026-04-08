from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.program.modules.handlers.teacherpreviewmodule import TeacherPreviewModule


class PreviewTeacherOverrideTests(SimpleTestCase):
    """Regression tests for admin teacher preview user overrides."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, user_value=None):
        params = {}
        if user_value is not None:
            params['user'] = user_value
        return self.factory.get('/teach/fake/teacherschedule', params)

    def test_non_admin_ignores_user_override(self):
        request = self._request(user_value='9999')
        non_admin = SimpleNamespace(isAdmin=lambda: False)
        request.user = non_admin

        resolved = TeacherPreviewModule._get_preview_teacher(None, request)

        self.assertIs(resolved, non_admin)

    def test_admin_invalid_user_override_raises_friendly_error(self):
        request = self._request(user_value='not-an-id')
        request.user = SimpleNamespace(isAdmin=lambda: True)

        with self.assertRaises(ESPError_NoLog) as ctx:
            TeacherPreviewModule._get_preview_teacher(None, request)

        self.assertIn('Invalid user override parameter', str(ctx.exception))

    def test_admin_missing_user_override_raises_friendly_error(self):
        request = self._request(user_value='12345')
        request.user = SimpleNamespace(isAdmin=lambda: True)

        with patch('esp.program.modules.handlers.teacherpreviewmodule.ESPUser.objects.filter') as mocked_filter:
            mocked_filter.return_value.first.return_value = None

            with self.assertRaises(ESPError_NoLog) as ctx:
                TeacherPreviewModule._get_preview_teacher(None, request)

        self.assertIn('No user found for the requested override ID', str(ctx.exception))

    def test_admin_valid_user_override_returns_teacher(self):
        request = self._request(user_value='77')
        request.user = SimpleNamespace(isAdmin=lambda: True)
        teacher = SimpleNamespace(id=77)

        with patch('esp.program.modules.handlers.teacherpreviewmodule.ESPUser.objects.filter') as mocked_filter:
            mocked_filter.return_value.first.return_value = teacher

            resolved = TeacherPreviewModule._get_preview_teacher(None, request)

        mocked_filter.assert_called_once_with(id=77)
        self.assertIs(resolved, teacher)

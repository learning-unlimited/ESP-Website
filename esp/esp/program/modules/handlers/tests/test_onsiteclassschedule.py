from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.onsiteclassschedule import OnsiteClassSchedule
from esp.users.models import ESPUser


class OnsiteClassScheduleUserParamTests(SimpleTestCase):
    """Regression tests for the 'user' GET parameter of the onsite schedule views."""

    def setUp(self):
        self.factory = RequestFactory()
        self.module = SimpleNamespace(program=SimpleNamespace(getUrlBase=lambda: 'Test/2222'))
        self.requester = SimpleNamespace(id=1)
        self.student = SimpleNamespace(id=2)

    def _request(self, params):
        request = self.factory.get('/onsite/Test/2222/studentschedule', params)
        request.user = self.requester
        return request

    def _studentschedule(self, params):
        fn = getattr(OnsiteClassSchedule.studentschedule, 'method', OnsiteClassSchedule.studentschedule)
        with patch(
            'esp.program.modules.handlers.onsiteclassschedule.ProgramPrintables.get_student_schedules',
            return_value=HttpResponse('schedule'),
        ) as get_schedules:
            resp = fn(self.module, self._request(params))
        return resp, get_schedules

    def _printschedule(self, params):
        fn = getattr(OnsiteClassSchedule.printschedule, 'method', OnsiteClassSchedule.printschedule)
        with patch('esp.program.modules.handlers.onsiteclassschedule.PrintRequest.objects.create') as create:
            resp = fn(self.module, self._request(params), None, None, None, None, None, None)
        return resp, create

    def _assert_user_not_found(self, resp):
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b'Could not find user', resp.content)

    def test_studentschedule_defaults_to_requester(self):
        resp, get_schedules = self._studentschedule({})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get_schedules.call_args.args[1], [self.requester])

    def test_studentschedule_uses_requested_user(self):
        with patch.object(ESPUser.objects, 'get', return_value=self.student) as get:
            resp, get_schedules = self._studentschedule({'user': '2'})
        get.assert_called_once_with(id=2)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get_schedules.call_args.args[1], [self.student])

    def test_studentschedule_non_numeric_user_returns_400(self):
        resp, get_schedules = self._studentschedule({'user': 'abc'})
        self._assert_user_not_found(resp)
        get_schedules.assert_not_called()

    def test_studentschedule_unknown_user_returns_400(self):
        with patch.object(ESPUser.objects, 'get', side_effect=ESPUser.DoesNotExist):
            resp, get_schedules = self._studentschedule({'user': '9999'})
        self._assert_user_not_found(resp)
        get_schedules.assert_not_called()

    def test_printschedule_uses_requested_user(self):
        with patch.object(ESPUser.objects, 'get', return_value=self.student):
            resp, create = self._printschedule({'user': '2', 'next': '/manage/userview'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/manage/userview')
        create.assert_called_once_with(user=self.student, printer=None)

    def test_printschedule_non_numeric_user_returns_400(self):
        resp, create = self._printschedule({'user': ''})
        self._assert_user_not_found(resp)
        create.assert_not_called()

    def test_printschedule_unknown_user_returns_400(self):
        with patch.object(ESPUser.objects, 'get', side_effect=ESPUser.DoesNotExist):
            resp, create = self._printschedule({'user': '9999'})
        self._assert_user_not_found(resp)
        create.assert_not_called()

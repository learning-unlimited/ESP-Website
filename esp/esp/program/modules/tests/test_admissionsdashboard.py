import json
import pytest

from django.test import RequestFactory

from esp.program.modules.handlers.admissionsdashboard import AdmissionsDashboard
from esp.application.models import StudentClassApp, StudentProgramApp


@pytest.fixture
def rf():
    return RequestFactory()


def test_apps_filters_non_admin_results(rf, mocker):
    """Teachers only see APPROVED applications."""
    dashboard = AdmissionsDashboard()

    request = rf.get("/")
    request.user = mocker.Mock()
    request.user.isAdmin.return_value = False
    request.user.getTaughtClassesFromProgram.return_value = []

    prog = mocker.Mock()
    mock_qs = mocker.MagicMock()
    mock_qs.filter.return_value = mock_qs
    mock_qs.__iter__.return_value = iter([])
    mocker.patch.object(StudentClassApp.objects, "filter", return_value=mock_qs)

    dashboard.apps(request, tl="teach", one=None, two=None, module=None, extra=None, prog=prog)

    mock_qs.filter.assert_any_call(app__admin_status=StudentProgramApp.APPROVED)


def test_apps_admin_sees_all(rf, mocker):
    """Admins bypass the APPROVED-only filter."""
    dashboard = AdmissionsDashboard()

    request = rf.get("/")
    request.user = mocker.Mock()
    request.user.isAdmin.return_value = True

    prog = mocker.Mock()
    mock_qs = mocker.MagicMock()
    mock_qs.filter.return_value = mock_qs
    mock_qs.__iter__.return_value = iter([])
    mocker.patch.object(StudentClassApp.objects, "filter", return_value=mock_qs)

    dashboard.apps(request, tl="manage", one=None, two=None, module=None, extra=None, prog=prog)

    assert not any(
        call.kwargs.get("app__admin_status") == StudentProgramApp.APPROVED
        for call in mock_qs.filter.call_args_list
    )


def test_app_missing_redirects(rf, mocker):
    """Missing StudentClassApp redirects via goToCore."""
    dashboard = AdmissionsDashboard()

    request = rf.get("/")
    request.user = mocker.Mock()

    prog = mocker.Mock()
    mocker.patch.object(StudentClassApp.objects, "get", side_effect=StudentClassApp.DoesNotExist)
    dashboard.goToCore = mocker.Mock(return_value="redirect")

    response = dashboard.app(request, tl="teach", one=None, two=None, module=None, extra=999, prog=prog)

    assert response == "redirect"


def test_update_apps_invalid_json(rf, mocker):
    """Invalid JSON in update_apps returns a structured error."""
    dashboard = AdmissionsDashboard()

    request = rf.post("/", {"changes": "invalid_json"})
    request.user = mocker.Mock()
    request.user.isAdmin.return_value = False
    request.user.getTaughtClassesFromProgram.return_value = []

    response = dashboard.update_apps(request, tl="teach", one=None, two=None, module=None, extra=None, prog=None)
    data = json.loads(response.content)

    assert data["success"] == 0
    assert "Invalid JSON" in data["error"]


def test_update_apps_skips_unauthorized(rf, mocker):
    """Unauthorized updates are silently skipped, not applied."""
    dashboard = AdmissionsDashboard()

    request = rf.post("/", {
        "changes": json.dumps({"1": {"teacher_rating": 5}})
    })
    request.user = mocker.Mock()
    request.user.isAdmin.return_value = False
    request.user.getTaughtClassesFromProgram.return_value = []

    prog = mocker.Mock()
    classapp = mocker.Mock()
    classapp.subject = "someclass"
    classapp.save = mocker.Mock()
    mocker.patch.object(StudentClassApp.objects, "get", return_value=classapp)

    response = dashboard.update_apps(request, tl="teach", one=None, two=None, module=None, extra=None, prog=prog)
    data = json.loads(response.content)

    assert data["updated"] == []
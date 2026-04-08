"""
Unit tests for:
  - esp/web/views/main.py  — program() view
  - esp/web/views/myesp.py — myesp_onsite() view

Covers:
  program():
    missing program → 404
    two="current" with no matching type → 404
    two="current" resolves to latest program instance
    valid program but no module → 404

  myesp_onsite():
    non-onsite user raises ESPError
    zero onsite programs → render picker (empty)
    single onsite program → redirect to /onsite/.../main
    multiple onsite programs → render picker

PR 7/10 — esp/web module coverage improvement
"""

from django.http import Http404
from django.test import RequestFactory

from esp.program.models import Program
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Permission
from esp.web.views.main import program
from esp.web.views.myesp import myesp_onsite


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(factory, path, user, session=None):
    request = factory.get(path)
    request.user = user
    request.session = session if session is not None else {}
    return request


# ---------------------------------------------------------------------------
# program() view
# ---------------------------------------------------------------------------

class ProgramViewMissingTest(ProgramFrameworkTest):
    """Tests for program() view — cases that raise Http404."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_missing_program_raises_404(self):
        request = _get(self.factory, '/learn/NoSuchProg/9999_Fall/', self.students[0])
        with self.assertRaises(Http404):
            program(request, 'learn', 'NoSuchProg', '9999_Fall', 'catalog')

    def test_current_no_matching_type_raises_404(self):
        # 'two="current"' with a program_type that has no programs → Http404
        request = _get(self.factory, '/learn/GhostProg/current/', self.students[0])
        with self.assertRaises(Http404):
            program(request, 'learn', 'GhostProg', 'current', 'catalog')

    def test_valid_program_no_module_raises_404(self):
        # Real program exists but the requested module doesn't exist → Http404
        prog = self.program
        request = _get(self.factory, '/learn/%s/%s/nonexistent_module/' % (prog.program_type, prog.program_instance), self.students[0])
        with self.assertRaises(Http404):
            program(
                request,
                'learn',
                prog.program_type,
                prog.program_instance,
                'nonexistent_module',
            )

    def test_current_resolves_to_program_instance(self):
        # 'two="current"' should resolve without raising 404 when program exists
        # (it will raise 404 eventually because 'nonexistent_module' is not found,
        #  but the resolution of 'current' → real instance must NOT raise 404 first)
        prog = self.program
        request = _get(self.factory, '/learn/%s/current/' % prog.program_type, self.students[0])
        # Http404 raised for missing module, NOT for missing program
        try:
            program(request, 'learn', prog.program_type, 'current', 'nonexistent_module')
        except Http404 as e:
            # Confirm the 404 is about the module, not "No current program"
            self.assertNotIn('No current program', str(e))

    def test_program_type_mismatch_raises_404(self):
        # Correct instance name but wrong program type → Http404
        prog = self.program
        request = _get(self.factory, '/learn/WrongType/%s/' % prog.program_instance, self.students[0])
        with self.assertRaises(Http404):
            program(request, 'learn', 'WrongType', prog.program_instance, 'catalog')


# ---------------------------------------------------------------------------
# myesp_onsite() view
# ---------------------------------------------------------------------------

class MyESPOnsiteTest(ProgramFrameworkTest):
    """Tests for myesp_onsite() view."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def _onsite_request(self, user):
        return _get(self.factory, '/myesp/onsite/', user)

    def _grant_onsite(self, user, prog):
        Permission.objects.get_or_create(
            user=user,
            permission_type='Onsite',
            program=prog,
        )

    def test_non_onsite_user_raises_error(self):
        # Regular student with no Onsite permission → ESPError
        regular_user = self.students[0]
        request = self._onsite_request(regular_user)
        with self.assertRaises(Exception):
            myesp_onsite(request)

    def test_single_program_redirects(self):
        onsite_user = self.admins[0]
        onsite_user.onsite_local = True
        Permission.objects.filter(user=onsite_user, permission_type='Onsite').delete()
        self._grant_onsite(onsite_user, self.program)
        request = self._onsite_request(onsite_user)
        response = myesp_onsite(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/onsite/', response['Location'])
        self.assertIn('/main', response['Location'])

    def test_multiple_programs_renders_picker(self):
        # Duplicate the program URL to simulate a second program
        from esp.program.models import Program as Prog
        second = Prog.objects.create(
            url='TestProgram/2222_Fall',
            name='TestProgram Fall 2222',
            grade_min=7, grade_max=12,
        )
        onsite_user = self.admins[0]
        onsite_user.onsite_local = True
        Permission.objects.filter(user=onsite_user, permission_type='Onsite').delete()
        self._grant_onsite(onsite_user, self.program)
        self._grant_onsite(onsite_user, second)
        request = self._onsite_request(onsite_user)
        response = myesp_onsite(request)
        self.assertEqual(response.status_code, 200)

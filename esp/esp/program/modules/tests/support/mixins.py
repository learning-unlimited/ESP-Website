"""
ModuleHandlerTestMixin — shared test infrastructure for program module handler tests.

WHY THIS EXISTS
---------------
Writing a test for any module handler currently requires:
  1. Reading ProgramFrameworkTest to understand setUp parameters
  2. Copy-pasting _setup_roles() (duplicated in 8+ test files)
  3. Manually building the module URL string
  4. Logging in as the right user
  5. Making the GET/POST request

This takes 30-60 minutes of boilerplate before writing a single assertion.
That friction is the primary reason high-consequence handlers like
finaidapprovemodule.py and adminreviewapps.py have 0% coverage today.

This mixin reduces handler test setup from ~10 lines to 2-3 lines —
permanently, for every future contributor, not just for this GSoC project.

USAGE
-----
    class MyHandlerTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
        def setUp(self):
            super().setUp()
            # optional: self.add_user_profiles(), self.schedule_randomly()

        def test_get_returns_200(self):
            self.login_as('admin')
            url = self.get_module_url('manage', 'finaidapprove')
            self.assert_view_ok(url)

        def test_non_admin_is_forbidden(self):
            self.login_as('student')
            url = self.get_module_url('manage', 'finaidapprove')
            self.assert_view_forbidden(url)

        def test_post_creates_record(self):
            self.login_as('admin')
            response = self.post_to_module('manage', 'finaidapprove', {'key': 'value'})
            self.assertEqual(response.status_code, 200)

ADDRESSES
---------
  Issue #3780 — Expand test coverage
  Issue #4480 — Improve test coverage properly
"""

from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj


class ModuleHandlerTestMixin:
    """
    Mixin for ProgramFrameworkTest subclasses that test module handlers.

    Requires self.program, self.admins, self.teachers, self.students to be
    set up by ProgramFrameworkTest.setUp() before any mixin method is called.

    URL pattern used throughout ESP:
        /<tl>/<program.url>/<view>
    e.g. /manage/TestProgram/2222_Summer/finaidapprove
    """

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------

    def login_as(self, role):
        """Log in as the first user of the given role.

        Args:
            role (str): One of 'admin', 'teacher', or 'student'.

        Returns:
            The ESPUser that was logged in.

        Raises:
            ValueError: If role is not one of the three accepted values.
            AssertionError: If login fails (wrong password or user not found).
        """
        role_map = {
            'admin':   self.admins,
            'teacher': self.teachers,
            'student': self.students,
        }
        if role not in role_map:
            raise ValueError(
                "Unknown role %r. Must be one of: %s"
                % (role, ', '.join(sorted(role_map)))
            )
        user = role_map[role][0]
        self.assertTrue(
            self.client.login(username=user.username, password='password'),
            "Could not log in as %s (username=%r). "
            "Check that ProgramFrameworkTest.setUp() created this user."
            % (role, user.username)
        )
        return user

    def logout(self):
        """Log out the current client session."""
        self.client.logout()

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def get_module_url(self, tl, view):
        """Build a module handler URL for the test program.

        Uses the same pattern as all existing ESP test files:
            /<tl>/<program.url>/<view>

        Args:
            tl (str):   The top-level namespace. One of:
                        'learn', 'teach', 'manage', 'onsite'.
            view (str): The view name, e.g. 'finaidapprove', 'makeaclass'.

        Returns:
            str: The full URL path, e.g. '/manage/TestProgram/2222_Summer/finaidapprove'

        Example:
            url = self.get_module_url('manage', 'finaidapprove')
            # -> '/manage/TestProgram/2222_Summer/finaidapprove'
        """
        return '/%s/%s/%s' % (tl, self.program.url, view)

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def assert_view_ok(self, url):
        """Assert that a GET request to url returns HTTP 200.

        Args:
            url (str): The URL to GET.

        Returns:
            HttpResponse: The response object for further assertions.
        """
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 200,
            "Expected HTTP 200 for GET %s, got %d. "
            "Check that the user is logged in and has the correct role."
            % (url, response.status_code)
        )
        return response

    def assert_view_forbidden(self, url):
        """Assert that a GET request to url returns HTTP 302 or 403.

        302 = redirect to login page (unauthenticated or wrong role).
        403 = explicitly forbidden.

        Both indicate the view is correctly protected.

        Args:
            url (str): The URL to GET.

        Returns:
            HttpResponse: The response object for further assertions.
        """
        response = self.client.get(url)
        self.assertIn(
            response.status_code, [302, 403],
            "Expected HTTP 302 or 403 for GET %s (access should be denied), "
            "got %d." % (url, response.status_code)
        )
        return response

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def post_to_module(self, tl, view, data=None):
        """POST data to a module handler view.

        Args:
            tl (str):          The top-level namespace ('learn', 'teach',
                               'manage', 'onsite').
            view (str):        The view name, e.g. 'finaidapprove'.
            data (dict|None):  POST data. Defaults to empty dict.

        Returns:
            HttpResponse: The response object.
        """
        url = self.get_module_url(tl, view)
        return self.client.post(url, data or {})

    def get_module_obj(self, handler_name):
        """Return the ProgramModuleObj for the given handler in the test program.

        Useful when a test needs to call handler methods directly rather than
        through the HTTP layer.

        Args:
            handler_name (str): The handler class name, e.g. 'FinAidApproveModule'.

        Returns:
            ProgramModuleObj: The module object for this program.

        Raises:
            ProgramModule.DoesNotExist: If no ProgramModule with that handler exists.
        """
        pm = ProgramModule.objects.get(handler=handler_name)
        return ProgramModuleObj.getFromProgModule(self.program, pm)

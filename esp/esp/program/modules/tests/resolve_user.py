from __future__ import absolute_import
from esp.program.tests import ProgramFrameworkTest
from esp.middleware.threadlocalrequest import get_current_request


class ResolveUserTest(ProgramFrameworkTest):
    """Tests for ProgramModuleObj._resolve_user() precedence rules.

    Verifies the three-level fallback introduced by issue #1968:
      1. Explicit user argument
      2. self.user (set by getModules)
      3. get_current_request().user (template / legacy fallback)
    """

    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj
        kwargs.update({'num_students': 2})
        super(ResolveUserTest, self).setUp(*args, **kwargs)

        m = ProgramModule.objects.filter(module_type='learn').first()
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def test_explicit_user_takes_priority_over_self_user(self):
        """Explicit argument must win over self.user."""
        self.moduleobj.user = self.students[0]
        resolved = self.moduleobj._resolve_user(self.students[1])
        self.assertEqual(resolved, self.students[1],
                         "_resolve_user should return the explicit argument, not self.user")

    def test_self_user_takes_priority_over_request(self):
        """self.user must win over get_current_request().user."""
        get_current_request().user = self.students[1]
        self.moduleobj.user = self.students[0]
        resolved = self.moduleobj._resolve_user(None)
        self.assertEqual(resolved, self.students[0],
                         "_resolve_user should return self.user when no explicit user is given")

    def test_fallback_to_request_user_when_no_self_user(self):
        """When neither explicit user nor self.user exists, fall back to request."""
        if hasattr(self.moduleobj, 'user'):
            del self.moduleobj.user
        get_current_request().user = self.students[0]
        resolved = self.moduleobj._resolve_user(None)
        self.assertEqual(resolved, self.students[0],
                         "_resolve_user should fall back to get_current_request().user")

    def test_getmodules_passes_user_to_isCompleted(self):
        """getModules(user) should sort modules using the explicit user, not request state."""
        # Set request user to student[1] — if fallback is used, ordering uses wrong user
        get_current_request().user = self.students[1]

        # getModules with explicit student[0] must attach student[0] to each module
        modules = self.program.getModules(self.students[0], 'learn')
        for m in modules:
            self.assertEqual(m.user, self.students[0],
                             "getModules should attach the explicit user to every module")

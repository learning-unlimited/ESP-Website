from __future__ import absolute_import
import logging

from django.http import HttpResponseRedirect

from esp.middleware import ESPError
from esp.program.controllers.testingutils import TestDataCleanupController
from esp.program.modules.base import ProgramModuleObj, aux_call, main_call, needs_admin
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.utils.web import render_to_response

logger = logging.getLogger(__name__)

_TEST_ROLES = ('Student', 'Teacher')
_TAG_KEYS = {
    'Student': 'test_student_id',
    'Teacher': 'test_teacher_id',
}


class AdminTestingModule(ProgramModuleObj):
    doc = """Provides per-program test accounts so admins can walk through
    student and teacher registration flows with real permissions and no
    risk of polluting production data."""

    @classmethod
    def module_properties(cls):
        return {
            'admin_title': 'Admin Testing Mode',
            'link_title': 'Testing Mode',
            'module_type': 'manage',
            'seq': 35,
            'choosable': 1,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_or_create_test_user(self, role):
        """Return the designated test account for *role* in this program.

        Created on first call; the PK is stored as a program-scoped Tag so
        no database migration is required.  The call is idempotent: if the
        Tag already points at a valid ESPUser that user is returned unchanged.
        """
        key = _TAG_KEYS[role]
        existing_id = Tag.getTag(key, target=self.program)
        if existing_id:
            try:
                return ESPUser.objects.get(pk=int(existing_id))
            except ESPUser.DoesNotExist:
                pass  # stale tag — fall through and recreate

        username = 'test_%s_%d' % (role.lower(), self.program.id)
        user, created = ESPUser.objects.get_or_create(
            username=username,
            defaults={
                'first_name': 'Test',
                'last_name': role,
                'email': '',
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
        # Always ensure the correct role group is set (idempotent).
        user.makeRole(role)
        Tag.setTag(key, target=self.program, value=str(user.pk))
        logger.info('Provisioned test %s account (pk=%d) for program %s',
                    role, user.pk, self.program)
        return user

    def _wipe_test_data(self, user):
        """Delete all registration data created by *user* in this program.

        Delegates to the TestDataCleanupController introduced in #4116 so
        that cleanup logic is not duplicated.
        """
        ctrl = TestDataCleanupController(self.program, user)
        ctrl.execute()
        logger.info('Wiped test data for user pk=%d in program %s',
                    user.pk, self.program)

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    @main_call
    @needs_admin
    def admin_testing(self, request, tl, one, two, module, extra, prog):
        """Landing page — shows test account status and action buttons."""
        accounts = {}
        for role in _TEST_ROLES:
            uid = Tag.getTag(_TAG_KEYS[role], target=prog)
            if uid:
                try:
                    accounts[role] = ESPUser.objects.get(pk=int(uid))
                except ESPUser.DoesNotExist:
                    accounts[role] = None
            else:
                accounts[role] = None

        context = {
            'module': self,
            'accounts': accounts,
            'reset': extra == 'reset_done',
        }
        return render_to_response(self.baseDir() + 'options.html', request, context)

    @aux_call
    @needs_admin
    def start_testing(self, request, tl, one, two, module, extra, prog):
        """Switch the admin session into a designated test account.

        *extra* must be 'student' or 'teacher'.  Unlike AdminMorph's
        switch_to_user (which sets user_morph and bleeds admin permissions
        through the needs_admin decorator), this performs a real login as
        the test user so the admin experiences the exact same permission
        set a real student or teacher would have.

        A 'testing_mode' dict is stored in the session so the
        stop_testing view can restore the admin session.
        """
        from django.contrib.auth import login, logout

        role_map = {'student': 'Student', 'teacher': 'Teacher'}
        role = role_map.get(extra)
        if role is None:
            raise ESPError('Unknown testing role "%s".' % extra, log=False)

        test_user = self._get_or_create_test_user(role)
        admin_user_id = request.user.pk
        admin_name = request.user.name()

        # Fully log out the admin and log in as the test user.
        # This avoids setting user_morph, so needs_admin will NOT
        # grant admin privileges to the test session.
        logout(request)
        test_user.backend = 'esp.utils.auth_backend.ESPAuthBackend'
        login(request, test_user)

        # Store enough info to restore the admin session later.
        request.session['testing_mode'] = {
            'admin_user_id': admin_user_id,
            'program_url': prog.getUrlBase(),
            'role': role,
        }

        logger.info('Admin "%s" started testing as %s (pk=%d) for program %s',
                    admin_name, role, test_user.pk, prog)
        response = HttpResponseRedirect('/')
        response.set_cookie('esp_testing_role', role, path='/')
        return response

    @aux_call
    @needs_admin
    def reset_testing(self, request, tl, one, two, module, extra, prog):
        """Wipe all registration data produced by the test accounts.

        Only accepts POST to guard against accidental resets from link
        pre-fetching.  Redirects back to the landing page on completion.
        """
        if request.method != 'POST':
            return HttpResponseRedirect('/manage/%s/admin_testing/' % prog.getUrlBase())

        for role in _TEST_ROLES:
            uid = Tag.getTag(_TAG_KEYS[role], target=prog)
            if uid:
                try:
                    user = ESPUser.objects.get(pk=int(uid))
                    self._wipe_test_data(user)
                except ESPUser.DoesNotExist:
                    pass

        logger.info('Admin reset testing data for program %s', prog)
        return HttpResponseRedirect(
            '/manage/%s/admin_testing/reset_done' % prog.getUrlBase()
        )

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

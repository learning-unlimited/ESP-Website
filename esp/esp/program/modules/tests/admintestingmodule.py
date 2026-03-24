from __future__ import absolute_import

from esp.program.models import ProgramModule, RegistrationProfile, StudentRegistration
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, Record, RecordType


class AdminTestingModuleTest(ProgramFrameworkTest):
    """Tests for AdminTestingModule: provisioning, exclusion, and cleanup."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 5, 'num_timeslots': 2, 'timeslot_length': 50,
                       'timeslot_gap': 10})
        super(AdminTestingModuleTest, self).setUp(*args, **kwargs)

        pm = ProgramModule.objects.get(handler='AdminTestingModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        self.admin = self.admins[0]
        self.admin.set_password('password')
        self.admin.save()

    # ------------------------------------------------------------------
    # Provisioning
    # ------------------------------------------------------------------

    def test_provision_creates_student_account(self):
        """start_testing/student creates and stores a test student account."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get(
            '/manage/%s/start_testing/student' % self.program.url,
        )
        uid = Tag.getTag('test_student_id', target=self.program)
        self.assertIsNotNone(uid)
        user = ESPUser.objects.get(pk=int(uid))
        self.assertTrue(user.isStudent())
        self.assertFalse(user.isAdministrator())

    def test_provision_creates_teacher_account(self):
        """start_testing/teacher creates and stores a test teacher account."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get(
            '/manage/%s/start_testing/teacher' % self.program.url,
        )
        uid = Tag.getTag('test_teacher_id', target=self.program)
        self.assertIsNotNone(uid)
        user = ESPUser.objects.get(pk=int(uid))
        self.assertTrue(user.isTeacher())
        self.assertFalse(user.isAdministrator())

    def test_provision_is_idempotent(self):
        """Calling start_testing twice gives back the same user."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        # switch back so we can call it again as admin
        self.client.get('/myesp/stop_testing/')
        uid_first = Tag.getTag('test_student_id', target=self.program)

        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        self.client.get('/myesp/stop_testing/')
        uid_second = Tag.getTag('test_student_id', target=self.program)

        self.assertEqual(uid_first, uid_second)

    def test_start_testing_sets_testing_mode_session(self):
        """start_testing stores testing_mode in the session."""
        self.client.login(username=self.admin.username, password='password')
        resp = self.client.get(
            '/manage/%s/start_testing/student' % self.program.url,
        )
        self.assertEqual(resp.status_code, 302)
        session = self.client.session
        self.assertIn('testing_mode', session)
        self.assertEqual(session['testing_mode']['role'], 'Student')
        self.assertEqual(session['testing_mode']['admin_user_id'], self.admin.pk)

    def test_start_testing_logs_in_as_test_user(self):
        """After start_testing the session user is the test user, not admin."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)

        uid = int(Tag.getTag('test_student_id', target=self.program))
        resp = self.client.get('/')
        self.assertEqual(resp.wsgi_request.user.pk, uid)

    def test_stop_testing_restores_admin(self):
        """stop_testing logs the admin back in and clears testing_mode."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        # Now logged in as test student
        resp = self.client.get('/myesp/stop_testing/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin_testing/', resp.url)
        # testing_mode should be cleared from the session
        session = self.client.session
        self.assertNotIn('testing_mode', session)
        # testing cookie should be cleared (delete_cookie sets value to '')
        self.assertEqual(self.client.cookies['esp_testing_role'].value, '')
        # Should be logged back in as admin
        resp2 = self.client.get('/')
        self.assertEqual(resp2.wsgi_request.user.pk, self.admin.pk)

    def test_admin_testing_landing_page(self):
        """admin_testing landing page loads for admin users."""
        self.client.login(username=self.admin.username, password='password')
        resp = self.client.get('/manage/%s/admin_testing/' % self.program.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Admin Testing Mode')

    def test_start_testing_rejects_invalid_role(self):
        """start_testing with an invalid role returns an error."""
        self.client.login(username=self.admin.username, password='password')
        resp = self.client.get(
            '/manage/%s/start_testing/invalid' % self.program.url,
        )
        self.assertContains(resp, 'Unknown testing role', status_code=500)

    def test_reset_requires_post(self):
        """reset_testing redirects on GET (no accidental resets)."""
        self.client.login(username=self.admin.username, password='password')
        resp = self.client.get('/manage/%s/reset_testing/' % self.program.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin_testing/', resp.url)

    # ------------------------------------------------------------------
    # Exclusion from student/teacher lists
    # ------------------------------------------------------------------

    def test_test_student_excluded_from_students_union(self):
        """Test student account does not appear in Program.students_union()."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        self.client.get('/myesp/stop_testing/')

        uid = int(Tag.getTag('test_student_id', target=self.program))
        test_user = ESPUser.objects.get(pk=uid)

        # Enroll the test student so they would normally appear.
        section = self.program.sections().first()
        section.preregister_student(test_user, fast_force_create=True)

        union = self.program.students_union()
        self.assertNotIn(test_user, union)

    def test_test_teacher_excluded_from_teachers_union(self):
        """Test teacher account does not appear in Program.teachers_union()."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/teacher' % self.program.url)
        self.client.get('/myesp/stop_testing/')

        uid = int(Tag.getTag('test_teacher_id', target=self.program))
        test_user = ESPUser.objects.get(pk=uid)

        union = self.program.teachers_union()
        self.assertNotIn(test_user, union)

    # ------------------------------------------------------------------
    # Cleanup / reset
    # ------------------------------------------------------------------

    def test_reset_deletes_student_registrations(self):
        """reset_testing deletes all StudentRegistration rows for the test user."""
        # Provision a test student and enroll them.
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        self.client.get('/myesp/stop_testing/')

        uid = int(Tag.getTag('test_student_id', target=self.program))
        test_user = ESPUser.objects.get(pk=uid)
        section = self.program.sections().first()
        section.preregister_student(test_user, fast_force_create=True)
        self.assertTrue(
            StudentRegistration.objects.filter(
                user=test_user,
                section__parent_class__parent_program=self.program,
            ).exists()
        )

        # Reset.
        self.client.login(username=self.admin.username, password='password')
        self.client.post('/manage/%s/reset_testing/' % self.program.url)

        self.assertFalse(
            StudentRegistration.objects.filter(
                user=test_user,
                section__parent_class__parent_program=self.program,
            ).exists()
        )

    def test_reset_deletes_records(self):
        """reset_testing deletes Record rows for the test user in this program."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        self.client.get('/myesp/stop_testing/')

        uid = int(Tag.getTag('test_student_id', target=self.program))
        test_user = ESPUser.objects.get(pk=uid)

        rt, _ = RecordType.objects.get_or_create(name='reg_confirmed')
        Record.objects.create(event=rt, program=self.program, user=test_user)
        self.assertTrue(
            Record.objects.filter(user=test_user, program=self.program).exists()
        )

        self.client.login(username=self.admin.username, password='password')
        self.client.post('/manage/%s/reset_testing/' % self.program.url)

        self.assertFalse(
            Record.objects.filter(user=test_user, program=self.program).exists()
        )

    def test_reset_deletes_registration_profile(self):
        """reset_testing removes RegistrationProfile rows for the test user."""
        self.client.login(username=self.admin.username, password='password')
        self.client.get('/manage/%s/start_testing/student' % self.program.url)
        self.client.get('/myesp/stop_testing/')

        uid = int(Tag.getTag('test_student_id', target=self.program))
        test_user = ESPUser.objects.get(pk=uid)
        RegistrationProfile.objects.get_or_create(
            user=test_user, program=self.program,
            defaults={'most_recent_profile': False},
        )
        self.assertTrue(
            RegistrationProfile.objects.filter(
                user=test_user, program=self.program
            ).exists()
        )

        self.client.login(username=self.admin.username, password='password')
        self.client.post('/manage/%s/reset_testing/' % self.program.url)

        self.assertFalse(
            RegistrationProfile.objects.filter(
                user=test_user, program=self.program
            ).exists()
        )

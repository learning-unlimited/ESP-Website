import json

from esp.application.models import StudentProgramApp, StudentClassApp
from esp.program.tests import ProgramFrameworkTest


class AdmissionsDashboardTest(ProgramFrameworkTest):
    """Tests for the AdmissionsDashboard handler."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)

        self.teacher = self.teachers[0]
        self.other_teacher = self.teachers[1]
        self.admin = self.admins[0]

        self.teacher_class = self.teacher.getTaughtClassesFromProgram(
            self.program
        )[0]
        self.other_class = self.other_teacher.getTaughtClassesFromProgram(
            self.program
        )[0]

    def create_class_app(
        self,
        student,
        subject,
        preference=1,
        admin_status=StudentProgramApp.UNREVIEWED,
    ):
        program_app = StudentProgramApp.objects.create(
            user=student,
            program=self.program,
            admin_status=admin_status,
        )

        return StudentClassApp.objects.create(
            app=program_app,
            subject=subject,
            student_preference=preference,
        )

    def test_teacher_apps_only_show_approved_own_classes(self):
        """Teachers see approved applications for their own classes only."""

        approved_app = self.create_class_app(
            self.students[0],
            self.teacher_class,
            admin_status=StudentProgramApp.APPROVED,
        )

        self.create_class_app(
            self.students[1],
            self.teacher_class,
            admin_status=StudentProgramApp.UNREVIEWED,
        )

        self.create_class_app(
            self.students[2],
            self.other_class,
            admin_status=StudentProgramApp.APPROVED,
        )

        self.assertTrue(
            self.client.login(
                username=self.teacher.username,
                password='password',
            )
        )

        response = self.client.get(
            f'{self.program.get_teach_url()}apps/'
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = {
            item['id'] for item in response.json()['apps']
        }
        self.assertEqual(returned_ids, {approved_app.id})

    def test_admin_manage_apps_include_unreviewed_applications(self):
        """Admins can see unreviewed applications in manage mode."""

        class_app = self.create_class_app(
            self.students[0],
            self.teacher_class,
        )

        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password',
            )
        )

        response = self.client.get(
            f'{self.program.get_manage_url()}apps/'
        )

        self.assertEqual(response.status_code, 200)

        returned_apps = {
            item['id']: item
            for item in response.json()['apps']
        }

        self.assertIn(class_app.id, returned_apps)
        self.assertEqual(
            returned_apps[class_app.id]['admin_status'],
            StudentProgramApp.UNREVIEWED,
        )

    def test_update_apps_skips_unauthorized_class_applications(self):
        """Teachers cannot update applications belonging to other teachers."""

        own_app = self.create_class_app(
            self.students[0],
            self.teacher_class,
        )

        unauthorized_app = self.create_class_app(
            self.students[1],
            self.other_class,
        )

        self.assertTrue(
            self.client.login(
                username=self.teacher.username,
                password='password',
            )
        )

        changes = {
            str(own_app.id): {
                'teacher_rating': StudentClassApp.GREEN,
                'teacher_comment': 'Reviewed by teacher',
            },
            str(unauthorized_app.id): {
                'teacher_rating': StudentClassApp.RED,
                'teacher_comment': 'Unauthorized change',
            },
        }

        response = self.client.post(
            f'{self.program.get_teach_url()}update_apps/',
            {'changes': json.dumps(changes)},
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertEqual(result['success'], 1)
        self.assertIn(str(own_app.id), result['updated'])
        self.assertNotIn(str(unauthorized_app.id), result['updated'])

        own_app.refresh_from_db()
        unauthorized_app.refresh_from_db()

        self.assertEqual(
            own_app.teacher_rating,
            StudentClassApp.GREEN,
        )
        self.assertEqual(
            own_app.teacher_comment,
            'Reviewed by teacher',
        )
        self.assertIsNone(unauthorized_app.teacher_rating)
        self.assertEqual(unauthorized_app.teacher_comment, '')

    def test_missing_class_app_redirects_to_core(self):
        """A missing class application redirects to the program core."""

        self.assertTrue(
            self.client.login(
                username=self.teacher.username,
                password='password',
            )
        )

        response = self.client.get(
            f'{self.program.get_teach_url()}app/999999/',
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('Location', response)

    def test_admin_manage_apps_show_admitted_and_waitlisted_classes(self):
        """Manage mode displays admitted and waitlisted class decisions."""

        program_app = StudentProgramApp.objects.create(
            user=self.students[0],
            program=self.program,
            admin_status=StudentProgramApp.APPROVED,
        )

        admitted_app = StudentClassApp.objects.create(
            app=program_app,
            subject=self.teacher_class,
            student_preference=1,
        )

        waitlisted_app = StudentClassApp.objects.create(
            app=program_app,
            subject=self.other_class,
            student_preference=2,
        )

        admitted_app.admit()
        waitlisted_app.waitlist()

        self.assertTrue(
            self.client.login(
                username=self.admin.username,
                password='password',
            )
        )

        response = self.client.get(
            f'{self.program.get_manage_url()}apps/'
        )

        self.assertEqual(response.status_code, 200)

        returned_apps = {
            item['id']: item
            for item in response.json()['apps']
        }

        self.assertIn(admitted_app.id, returned_apps)

        decision_status = returned_apps[
            admitted_app.id
        ]['decision_status']

        self.assertIn(
            f'Admitted: {self.teacher_class.title}',
            decision_status,
        )
        self.assertIn(
            f'Waitlisted: {self.other_class.title}',
            decision_status,
        )

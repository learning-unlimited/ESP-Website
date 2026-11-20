from django.test import RequestFactory

from esp.admin import admin_site
from esp.program.admin import StudentAppAdmin
from esp.program.models.app_ import StudentApplication, StudentAppQuestion
from esp.program.tests import ProgramFrameworkTest


class StudentApplicationInstantiationTest(ProgramFrameworkTest):
    """ Regression tests for #4554.

    StudentApplication.__init__() used to call save() and set_questions(),
    which meant merely constructing an instance wrote to the database.
    """

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 2, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.question = StudentAppQuestion.objects.create(
            program=self.program,
            question='Why do you want to attend?',
        )

    def test_blank_instance_is_not_saved(self):
        #   This is what the admin's "Add student application" page does; it
        #   used to raise IntegrityError on program_id.
        app = StudentApplication()
        self.assertIsNone(app.pk)
        self.assertFalse(StudentApplication.objects.exists())

    def test_instance_with_fks_is_not_saved_until_asked(self):
        app = StudentApplication(user=self.students[0], program=self.program)
        self.assertIsNone(app.pk)
        self.assertFalse(StudentApplication.objects.exists())

        app.save()
        self.assertIsNotNone(app.pk)

    def test_loading_does_not_rewrite_rows(self):
        app = StudentApplication(user=self.students[0], program=self.program)
        app.save()

        #   Instances built by the ORM go through __init__ too, so the old
        #   code re-saved every row on read.  One SELECT is all this needs.
        with self.assertNumQueries(1):
            self.assertEqual(len(list(StudentApplication.objects.all())), 1)

    def test_set_questions_is_a_noop_while_unsaved(self):
        app = StudentApplication(user=self.students[0], program=self.program)
        app.set_questions()
        self.assertFalse(StudentApplication.objects.exists())

        app = StudentApplication()
        app.set_questions()
        self.assertFalse(StudentApplication.objects.exists())

    def test_questions_are_set_on_creation(self):
        app = StudentApplication(user=self.students[0], program=self.program)
        app.save()
        self.assertIn(self.question, app.questions.all())


class StudentAppAdminTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 1, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)

    def test_add_is_not_offered(self):
        #   program and user are editable=False, so the add form could never
        #   populate them and submitting it could only fail.
        admin = StudentAppAdmin(StudentApplication, admin_site)
        self.assertFalse(admin.has_add_permission(RequestFactory().get('/')))

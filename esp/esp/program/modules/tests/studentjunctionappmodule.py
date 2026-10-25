"""
Unit tests for StudentJunctionAppModule (studentjunctionappmodule.py).
"""
from esp.program.models import RegistrationType, StudentRegistration
from esp.program.models.app_ import StudentApplication, StudentAppQuestion
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest


class StudentJunctionAppModuleTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 4, 'num_teachers': 1, 'num_admins': 1})
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.module = self.get_module_obj('StudentJunctionAppModule')
        StudentAppQuestion.objects.create(
            program=self.program,
            question='Why do you want to attend?',
            directions='Write a short paragraph.',
        )

    def _make_app(self, student, done=False):
        app = StudentApplication(user=student, program=self.program, done=done)
        app.save()
        return app

    def test_is_using_student_apps(self):
        self.assertTrue(self.program.isUsingStudentApps())

    def test_students_queryset_started(self):
        student = self.students[0]
        self._make_app(student, done=False)
        result = self.module.students(QObject=False)
        self.assertIn(student, result['studentapps'])
        self.assertNotIn(student, result['studentapps_complete'])

    def test_students_queryset_complete(self):
        student = self.students[1]
        self._make_app(student, done=True)
        result = self.module.students(QObject=False)
        self.assertIn(student, result['studentapps_complete'])
        self.assertIn(student, result['studentapps'])

    def test_students_qobject_keys(self):
        result = self.module.students(QObject=True)
        self.assertIn('studentapps', result)
        self.assertIn('studentapps_complete', result)
        self.assertIn('app_accepted_to_one_program', result)

    def test_is_completed_when_done(self):
        student = self.students[0]
        app = student.getApplication(self.program)
        app.done = True
        app.save()
        self.assertTrue(self.module.isCompleted(user=student))

    def test_is_completed_when_no_questions(self):
        StudentAppQuestion.objects.filter(program=self.program).delete()
        StudentAppQuestion.objects.filter(subject__parent_program=self.program).delete()
        student = self.students[2]
        app = student.getApplication(self.program)
        app.done = False
        app.save()
        app.questions.clear()
        self.assertTrue(self.module.isCompleted(user=student))

    def test_is_completed_false_with_unanswered_class_questions(self):
        student = self.students[3]
        cls = self.program.classes()[0]
        cls.studentappquestion_set.create(
            question='Why this class?',
            directions='',
        )
        sec = cls.get_sections()[0]
        rt, _ = RegistrationType.objects.get_or_create(
            name='Applied', defaults={'category': 'student'}
        )
        StudentRegistration.objects.get_or_create(
            user=student, section=sec, relationship=rt
        )
        app = student.getApplication(self.program)
        app.done = False
        app.save()
        app.set_questions()
        app.responses.clear()
        self.assertTrue(
            app.questions.exists(),
            "Setup must attach at least one application question before asserting incompleteness",
        )
        self.assertFalse(self.module.isCompleted(user=student))

    def test_student_desc_keys(self):
        desc = self.module.studentDesc()
        self.assertIn('studentapps', desc)
        self.assertIn('studentapps_complete', desc)

    def test_is_step_when_apps_enabled(self):
        self.assertTrue(self.module.isStep())

    def test_students_empty_when_apps_disabled(self):
        StudentAppQuestion.objects.filter(program=self.program).delete()
        StudentAppQuestion.objects.filter(subject__parent_program=self.program).delete()
        self.assertEqual(self.module.students(QObject=False), {})

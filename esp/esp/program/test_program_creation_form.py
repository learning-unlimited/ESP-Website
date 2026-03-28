from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from esp.program.forms import ProgramCreationForm
from esp.program.models import ProgramModule, ClassCategories
from esp.users.models import ESPUser


class ProgramCreationFormDateValidationTest(TestCase):
    def setUp(self):
        user_role_setup()
        self.admin, _ = ESPUser.objects.get_or_create(
            username='newprogram_admin_test',
            defaults={
                'first_name': 'NewProgram',
                'last_name': 'Admin',
                'email': 'newprogram_admin_test@example.com',
            },
        )
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.category, _ = ClassCategories.objects.get_or_create(
            category='Test Category',
            symbol='T',
        )

    def _base_data(self):
        return {
            'term': '2099_Fall',
            'term_friendly': 'Fall 2099',
            'grade_min': '7',
            'grade_max': '12',
            'director_email': 'info@test.learningu.org',
            'director_cc_email': '',
            'director_confidential_email': '',
            'program_size_max': '3000',
            'program_allow_waitlist': False,
            'program_type': 'DateValidationProgram',
            'program_modules': [m.id for m in ProgramModule.objects.all()],
            'program_module_questions': [],
            'class_categories': [self.category.id],
            'flag_types': [],
            'admins': [self.admin.id],
            'teacher_reg_start': '2099-01-01 10:00:00',
            'teacher_reg_end': '2099-01-02 10:00:00',
            'student_reg_start': '2099-01-03 10:00:00',
            'student_reg_end': '2099-01-04 10:00:00',
            'base_cost': '0',
            'sibling_discount': '0',
        }

    def test_rejects_teacher_registration_with_end_before_start(self):
        data = self._base_data()
        data['teacher_reg_start'] = '2099-01-02 10:00:00'
        data['teacher_reg_end'] = '2099-01-01 10:00:00'

        form = ProgramCreationForm(data)

        self.assertFalse(form.is_valid())
        self.assertIn('teacher_reg_end', form.errors)

    def test_rejects_student_registration_with_end_before_start(self):
        data = self._base_data()
        data['student_reg_start'] = '2099-01-04 10:00:00'
        data['student_reg_end'] = '2099-01-03 10:00:00'

        form = ProgramCreationForm(data)

        self.assertFalse(form.is_valid())
        self.assertIn('student_reg_end', form.errors)

    def test_accepts_valid_registration_ranges(self):
        data = self._base_data()

        form = ProgramCreationForm(data)

        self.assertTrue(form.is_valid(), form.errors)

from unittest.mock import patch

from django.db import IntegrityError

from esp.accounting.controllers import ProgramAccountingController
from esp.accounting.models import Account
from esp.program.models import ClassCategories, Program, ProgramModule
from esp.tests.util import CacheFlushTestCase as TestCase, user_role_setup
from esp.users.models import ESPUser


class NewProgramCreationRegressionTest(TestCase):
    def setUp(self):
        user_role_setup()

        self.admin = ESPUser.objects.create_user(
            first_name='Admin',
            last_name='User',
            username='programadmin',
            email='programadmin@test.learningu.org',
        )
        self.admin.set_password('pubbasswubbord')
        self.admin.save()
        self.admin.makeRole('Administrator')

        self.client.login(username=self.admin.username, password='pubbasswubbord')

        ClassCategories.objects.create(symbol='X', category='Everything')
        ClassCategories.objects.create(symbol='N', category='Nothing')
        ProgramModule.objects.create(
            link_title='Default Module',
            admin_title='Default Module (do stuff)',
            module_type='learn',
            handler='StudentRegCore',
            seq=0,
            required=False,
        )
        ProgramModule.objects.create(
            link_title='Register Your Classes',
            admin_title='Teacher Class Registration',
            module_type='teach',
            handler='TeacherClassRegModule',
            inline_template='listclasses.html',
            seq=10,
            required=False,
        )
        ProgramModule.objects.create(
            link_title='Sign up for Classes',
            admin_title='Student Class Registration',
            module_type='learn',
            handler='StudentClassRegModule',
            seq=10,
            required=True,
        )
        ProgramModule.objects.create(
            link_title='Sign up for a Program',
            admin_title='Student Registration Core',
            module_type='learn',
            handler='StudentRegCore',
            seq=-9999,
            required=False,
        )

    def _program_post_data(self):
        return {
            'term': '3001_Winter',
            'term_friendly': 'Winter 3001',
            'grade_min': '7',
            'grade_max': '12',
            'director_email': 'info@test.learningu.org',
            'director_cc_email': '',
            'director_confidential_email': '',
            'program_size_max': '3000',
            'program_type': 'Prubbogrubbam!',
            'program_modules': [x.id for x in ProgramModule.objects.all()],
            'class_categories': [x.id for x in ClassCategories.objects.all()],
            'teacher_reg_start': '2000-01-01 00:00:00',
            'teacher_reg_end': '3001-01-01 00:00:00',
            'student_reg_start': '2000-01-01 00:00:00',
            'student_reg_end': '3001-01-01 00:00:00',
            'base_cost': '666',
            'sibling_discount': '',
        }

    def test_newprogram_rolls_back_on_account_setup_conflict(self):
        with patch(
            'esp.program.setup.ProgramAccountingController.setup_accounts',
            side_effect=IntegrityError('duplicate account'),
        ):
            response = self.client.post('/manage/newprogram', self._program_post_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No changes were saved')
        self.assertEqual(Program.objects.count(), 0)
        self.assertEqual(Account.objects.count(), 0)

    def test_setup_accounts_uses_unique_name_per_program(self):
        shared_name = 'Splash Spring 2026'
        program_a = Program.objects.create(
            url='Splash/2026_A',
            name=shared_name,
            grade_min=7,
            grade_max=12,
        )
        program_b = Program.objects.create(
            url='Splash/2026_B',
            name=shared_name,
            grade_min=7,
            grade_max=12,
        )

        account_a = ProgramAccountingController(program_a).setup_accounts()
        account_b = ProgramAccountingController(program_b).setup_accounts()

        self.assertEqual(account_a.program, program_a)
        self.assertEqual(account_b.program, program_b)
        self.assertNotEqual(account_a.id, account_b.id)
        self.assertNotEqual(account_a.name, account_b.name)
        self.assertTrue(account_a.name.startswith(f'program-{program_a.id}-'))
        self.assertTrue(account_b.name.startswith(f'program-{program_b.id}-'))

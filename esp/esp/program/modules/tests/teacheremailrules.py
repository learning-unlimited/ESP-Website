# -*- coding: utf-8 -*-
# Tests for per-program teacher email validation (Issue #3639)

from datetime import datetime

from esp.program.tests import ProgramFrameworkTest
from esp.program.models import RegistrationProfile
from esp.program.modules.module_ext import TeacherEmailRules, MODE_BLOCK, MODE_WARN
from esp.users.models import ContactInfo, TeacherInfo
from esp.middleware.threadlocalrequest import get_current_request


class TeacherEmailRulesTest(ProgramFrameworkTest):
    """Unit and integration tests for TeacherEmailRules."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.rules, _ = TeacherEmailRules.objects.get_or_create(
            program=self.program,
            defaults={'enabled': True, 'allowed_domains': 'school.edu', 'mode': MODE_WARN},
        )

    def test_disabled_rules_allow_any_email(self):
        self.rules.enabled = False
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('anyone@gmail.com')
        self.assertTrue(valid)
        self.assertFalse(warn)

    def test_domain_match_allows(self):
        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu, university.edu'
        self.rules.regex_pattern = ''
        self.rules.mode = MODE_BLOCK
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('teacher@school.edu')
        self.assertTrue(valid)
        valid, msg, warn = self.rules.validate_teacher_email('other@UNIVERSITY.EDU')
        self.assertTrue(valid)

    def test_domain_mismatch_block_mode(self):
        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu'
        self.rules.regex_pattern = ''
        self.rules.mode = MODE_BLOCK
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('teacher@gmail.com')
        self.assertFalse(valid)
        self.assertFalse(warn)

    def test_domain_mismatch_warn_mode(self):
        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu'
        self.rules.regex_pattern = ''
        self.rules.mode = MODE_WARN
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('teacher@gmail.com')
        self.assertTrue(valid)
        self.assertTrue(warn)
        self.assertTrue(len(msg) > 0)

    def test_regex_match_allows(self):
        self.rules.enabled = True
        self.rules.allowed_domains = ''
        self.rules.regex_pattern = r'.*@school\.edu$'
        self.rules.mode = MODE_BLOCK
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('x@school.edu')
        self.assertTrue(valid)

    def test_regex_mismatch_block(self):
        self.rules.enabled = True
        self.rules.allowed_domains = ''
        self.rules.regex_pattern = r'.*@school\.edu$'
        self.rules.mode = MODE_BLOCK
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('x@gmail.com')
        self.assertFalse(valid)

    def test_empty_email_allowed_when_disabled(self):
        self.rules.enabled = False
        self.rules.save()
        valid, msg, warn = self.rules.validate_teacher_email('')
        self.assertTrue(valid)

    def test_requires_profile_confirmation_when_rules_enabled(self):
        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu'
        self.rules.mode = MODE_BLOCK
        self.rules.save()
        self.assertTrue(self.rules.requires_profile_confirmation('teacher@gmail.com'))
        self.assertFalse(self.rules.requires_profile_confirmation('teacher@school.edu'))

    def test_get_last_for_program_does_not_auto_save_teacher_with_block_rules(self):
        """Teachers with non-matching emails must not auto-complete profile when rules are enabled."""
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        teacher = self.teachers[0]
        teacher.email = 'teacher@gmail.com'
        teacher.save()

        contact = ContactInfo(
            user=teacher,
            e_mail='teacher@gmail.com',
            first_name=teacher.first_name,
            last_name=teacher.last_name,
        )
        contact.save()
        teacher_info = TeacherInfo(user=teacher, affiliation='Other', graduation_year='2020')
        teacher_info.save()

        profile = RegistrationProfile(
            user=teacher,
            program=None,
            contact_user=contact,
            teacher_info=teacher_info,
            most_recent_profile=True,
            last_ts=datetime.now(),
        )
        profile.save()

        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu'
        self.rules.mode = MODE_BLOCK
        self.rules.save()

        get_current_request().user = teacher
        prof = RegistrationProfile.getLastForProgram(teacher, self.program, 'teach')
        self.assertIsNone(prof.id)

        module = ProgramModule.objects.get(handler='RegProfileModule', module_type='teach')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, module)
        self.assertFalse(moduleobj.isCompleted(teacher))

    def test_teacher_profile_form_blocks_non_matching_email(self):
        from esp.users.forms.user_profile import TeacherProfileForm

        teacher = self.teachers[1]
        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu'
        self.rules.mode = MODE_BLOCK
        self.rules.save()

        data = {
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'e_mail': 'teacher@gmail.com',
            'phone_day': '',
            'phone_cell': '+16175551234',
            'address_street': '',
            'address_city': '',
            'address_state': 'MA',
            'address_zip': '',
            'address_country': '',
            'affiliation': 'Other:MIT',
            'graduation_year': '2020',
        }
        form = TeacherProfileForm(teacher, data, program=self.program, role='teacher')
        self.assertFalse(form.is_valid())

    def test_teacher_profile_form_warns_on_non_matching_email(self):
        from esp.users.forms.user_profile import TeacherProfileForm

        teacher = self.teachers[2]
        self.rules.enabled = True
        self.rules.allowed_domains = 'school.edu'
        self.rules.mode = MODE_WARN
        self.rules.save()

        data = {
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'e_mail': 'teacher@gmail.com',
            'phone_day': '',
            'phone_cell': '+16175551234',
            'address_street': '',
            'address_city': '',
            'address_state': 'MA',
            'address_zip': '',
            'address_country': '',
            'affiliation': 'Other:MIT',
            'graduation_year': '2020',
        }
        form = TeacherProfileForm(teacher, data, program=self.program, role='teacher')
        self.assertTrue(form.is_valid())
        self.assertTrue(getattr(form, '_teacher_email_warning', None))

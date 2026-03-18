# -*- coding: utf-8 -*-
# Tests for per-program teacher email validation (Issue #3639)

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.module_ext import TeacherEmailRules, MODE_BLOCK, MODE_WARN


class TeacherEmailRulesTest(ProgramFrameworkTest):
    """Unit tests for TeacherEmailRules.validate_teacher_email."""

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

from __future__ import absolute_import

from unittest import mock

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from esp.dbmail.models import send_mail, AllowedSenderDomainValidator


class SendMailTest(TestCase):
    def test_cc(self):
        """ cc addresses get a Cc header and are actually delivered to,
        alongside the To and Bcc recipients. """
        mail.outbox = []
        send_mail('Subject', 'Body', settings.SERVER_EMAIL, ['to@example.com'],
                  bcc=['bcc@example.com'], cc=['cc@example.com'])
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.cc, ['cc@example.com'])
        self.assertEqual(set(message.recipients()),
                         {'to@example.com', 'cc@example.com', 'bcc@example.com'})
        self.assertIn('Cc: cc@example.com', message.message().as_string())
        self.assertNotIn('bcc@example.com', message.message().as_string())


class AllowedSenderDomainValidatorTest(TestCase):
    @override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'mit\.edu'])
    def test_uses_this_sites_domains(self):
        """ Validates against the current site's settings, not whatever they
        were when the model was defined. """
        validate = AllowedSenderDomainValidator()
        validate('splash@mit.edu')
        with self.assertRaises(ValidationError) as cm:
            validate('splash@esp-dev.mit.edu')
        self.assertEqual(cm.exception.messages, [r'Domain must match one of: mit\.edu'])
        with override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'mit\.edu', r'esp-dev\.mit\.edu']):
            validate('splash@esp-dev.mit.edu')
        for bad in ['splash@example.com', 'splash@mit.edu.example.com', '']:
            with self.assertRaises(ValidationError):
                validate(bad)

    def test_migration_state_is_the_same_on_every_site(self):
        """ The field deconstructs (and so appears in migrations) identically
        whatever the site's allowed domains, so `migrate` doesn't see
        unmigrated changes on sites whose domains differ from the generating
        one's. """
        from esp.program.models import Program
        field = Program._meta.get_field('director_email')
        with override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'mit\.edu']):
            one = field.deconstruct()
        with override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'esp\.mit\.edu', r'esp-dev\.mit\.edu']):
            other = field.deconstruct()
        self.assertEqual(one, other)
        self.assertEqual(one[3]['validators'], [AllowedSenderDomainValidator()])


class ClassMailingListCreationTest(TestCase):
    """ How the class/section list handlers drive Mailman when they create a
    list. Every Mailman call is mocked, so this checks the order and content
    of the calls, not Mailman itself.

    The activation notice for a new students list goes to the class's
    teachers list. A brand-new Mailman list holds non-member posts until the
    teachers handler applies its settings, so if both lists are created at
    once the notice would be held for moderation (as happened for s16774 on
    2026-11-19). The teachers handler fixes this by releasing such held
    posts in the same locked Mailman call that opens the list. """

    MAILMAN_FUNCS = ['create_list', 'load_list_settings', 'apply_list_settings',
                     'add_list_member', 'add_list_members',
                     'set_list_moderator_password', 'send_mail']

    def run_handler(self, handler_name, user_type, apply_result=0):
        """ Run SectionList or ClassList for class 'S123' (section 1) and
        return a mock recording every Mailman call in order. """
        from esp.dbmail.receivers import classlist, sectionlist
        module = {'SectionList': sectionlist, 'ClassList': classlist}[handler_name]

        cls = mock.Mock()
        cls.emailcode.return_value = 'S123'
        cls.get_teachers.return_value = []
        cls.parent_program.director_email = 'director@example.com'
        cls.parent_program.niceName.return_value = 'Splash 2026'
        section = mock.Mock()
        section.index.return_value = 1
        section.emailcode.return_value = 'S123s1'
        section.students.return_value = []
        cls.sections.all.return_value = [section]

        calls = mock.Mock()
        calls.apply_list_settings.return_value = apply_result
        calls.set_list_moderator_password.return_value = 'modpass'
        patches = [mock.patch.object(module, name, getattr(calls, name))
                   for name in self.MAILMAN_FUNCS]
        patches.append(mock.patch.object(module.ClassSubject.objects, 'get',
                                         return_value=cls))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

        handler = getattr(module, handler_name)(None, None)
        with override_settings(USE_MAILMAN=True):
            if handler_name == 'SectionList':
                handler.process(None, '123', '1', user_type)
            else:
                handler.process(None, '123', user_type)
        self.assertTrue(handler.send)
        return calls

    def teachers_address(self):
        return 'S123-teachers@%s' % Site.objects.get_current().domain

    def test_students_list_sends_notice_to_class_teachers_list(self):
        """ The notice goes to the class-level teachers list. If that list is
        still being set up, the teachers handler releases the notice once it
        is (see the next test), so nothing here touches the teachers list. """
        for handler_name in ['SectionList', 'ClassList']:
            with self.subTest(handler=handler_name):
                calls = self.run_handler(handler_name, 'students')
                calls.send_mail.assert_called_once()
                self.assertEqual(calls.send_mail.call_args[0][3],
                                 [self.teachers_address()])
                for c in calls.apply_list_settings.call_args_list:
                    self.assertNotIn('teachers', c[0][0])

    def test_teachers_list_settings_in_one_call_after_config_file(self):
        """ The teachers list accepts non-member posts, set in a single
        Mailman call right after the config file is loaded, which also
        releases posts held from non-members before it ran. """
        for handler_name in ['SectionList', 'ClassList']:
            with self.subTest(handler=handler_name):
                calls = self.run_handler(handler_name, 'teachers')
                names = [c[0] for c in calls.mock_calls]
                self.assertEqual(names[:3], ['create_list',
                                             'load_list_settings',
                                             'apply_list_settings'])
                self.assertEqual(names.count('apply_list_settings'), 1)
                list_name, applied = calls.apply_list_settings.call_args[0]
                # SectionList's own teachers list is per section; the
                # activation notice always goes to the class-level one,
                # which ClassList creates.
                self.assertEqual(list_name, {'SectionList': 'S123s1-teachers',
                                             'ClassList': 'S123-teachers'}[handler_name])
                self.assertEqual(applied['generic_nonmember_action'], 0)
                self.assertIs(applied['default_member_moderation'], False)
                self.assertEqual(applied['subject_prefix'], '[Splash 2026]')
                self.assertEqual(calls.apply_list_settings.call_args[1],
                                 {'release_nonmember_holds': True})
                calls.send_mail.assert_not_called()

    def test_class_config_file_leaves_nonmember_action_alone(self):
        """ load_list_settings() applies lists/class_mailman.config. If it set
        generic_nonmember_action, it could undo the teachers list's setting
        when both lists are being created at once. """
        import os
        path = os.path.join(settings.PROJECT_ROOT, 'lists/class_mailman.config')
        config = {}
        with open(path) as f:
            exec(f.read(), config)
        self.assertNotIn('generic_nonmember_action', config)


class ApplyListSettingsTest(TestCase):
    """ esp.mailman.apply_list_settings() writes a file that Mailman's
    config_list runs as Python 2 with the list locked. """

    def written_config(self, **kwargs):
        # The module's functions become no-ops at import time unless
        # USE_MAILMAN is on, so load a separate copy of it with it on.
        import importlib.util
        import esp.mailman
        spec = importlib.util.spec_from_file_location(
            'esp_mailman_under_test', esp.mailman.__file__)
        mailman = importlib.util.module_from_spec(spec)
        with override_settings(USE_MAILMAN=True, MAILMAN_PATH='/fake/',
                               MAILMAN_PASSWORD='x'):
            spec.loader.exec_module(mailman)
        written = {}

        def fake_call(args):
            with open(args[2]) as f:
                written['text'] = f.read()
            written['args'] = args
            return 0

        with mock.patch.object(mailman, 'call', fake_call):
            result = mailman.apply_list_settings(
                's1-teachers', {'generic_nonmember_action': 0}, **kwargs)
        self.assertEqual(result, 0)
        self.assertEqual(written['args'][1:2] + written['args'][3:],
                         ['-i', 's1-teachers'])
        return written['text']

    def test_settings_only_by_default(self):
        self.assertEqual(self.written_config(),
                         'generic_nonmember_action = 0\n')

    def test_release_nonmember_holds(self):
        from esp.mailman import RELEASE_NONMEMBER_HOLDS
        text = self.written_config(release_nonmember_holds=True)
        self.assertEqual(text, RELEASE_NONMEMBER_HOLDS +
                         'generic_nonmember_action = 0\n')
        # config_list sets every leftover global as a list attribute, so the
        # code must not leave any behind.
        self.assertTrue(text.rstrip().splitlines()[-2].startswith(
            'del _release_nonmember_holds'))

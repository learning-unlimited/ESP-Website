from __future__ import absolute_import

import traceback
from re import escape as re_escape
from unittest import mock

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from esp.dbmail.models import send_mail, AllowedSenderDomainValidator
from esp.users.models import ESPUser


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
    once the notice would be held for moderation. The teachers handler fixes
    this by releasing such held posts once the list is set up and its members
    are added: a released post goes only to the members the list has at that
    moment. """

    MAILMAN_FUNCS = ['create_list', 'apply_list_settings', 'add_list_members',
                     'set_list_moderator_password', 'send_mail']

    def run_handler(self, handler_name, user_type, apply_result=0, create_result=None, students=()):
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
        section.students.return_value = list(students)
        cls.sections.all.return_value = [section]

        calls = self.last_calls = mock.Mock()
        if create_result is not None:
            calls.create_list.side_effect = create_result
        if isinstance(apply_result, Exception):
            calls.apply_list_settings.side_effect = apply_result
        else:
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

    def test_students_list_members_in_one_call(self):
        """ A students list gets its students, the teachers and the director
        in one add_members run; a teachers list gets no students. """
        for handler_name in ['SectionList', 'ClassList']:
            for user_type in ['students', 'teachers']:
                with self.subTest(handler=handler_name, user_type=user_type):
                    calls = self.run_handler(handler_name, user_type, students=['s@example.com'])
                    calls.add_list_members.assert_called_once()
                    added = calls.add_list_members.call_args[0][1]
                    self.assertIn('director@example.com', added)
                    self.assertEqual('s@example.com' in added, user_type == 'students')

    def test_existing_list_keeps_its_moderator_password(self):
        """ If the list already existed (two first emails at once, or a retry),
        the setup is redone but the moderator password isn't reset and no
        second notice goes out: the first notice's password must keep working. """
        for handler_name in ['SectionList', 'ClassList']:
            with self.subTest(handler=handler_name):
                calls = self.run_handler(handler_name, 'students', create_result=[False])
                calls.set_list_moderator_password.assert_not_called()
                calls.send_mail.assert_not_called()
                calls.apply_list_settings.assert_called_once()
                calls.add_list_members.assert_called_once()
                calls = self.run_handler(handler_name, 'students', create_result=[True])
                calls.set_list_moderator_password.assert_called_once()
                calls.send_mail.assert_called_once()

    def test_teachers_list_settings_right_after_config_file(self):
        """ The teachers list accepts non-member posts, set in the same
        Mailman call (config_list run) that applies the config file, right
        after the list is created. """
        for handler_name in ['SectionList', 'ClassList']:
            with self.subTest(handler=handler_name):
                calls = self.run_handler(handler_name, 'teachers')
                names = [c[0] for c in calls.mock_calls]
                self.assertEqual(names[:2], ['create_list', 'apply_list_settings'])
                (list_name,), kwargs = calls.apply_list_settings.call_args_list[0]
                applied = kwargs.pop('data')
                self.assertEqual(kwargs, {'listfile': 'lists/class_mailman.config', 'errors': 'log'})
                # SectionList's own teachers list is per section; the
                # activation notice always goes to the class-level one,
                # which ClassList creates.
                self.assertEqual(list_name, {'SectionList': 'S123s1-teachers',
                                             'ClassList': 'S123-teachers'}[handler_name])
                self.assertEqual(applied['generic_nonmember_action'], 0)
                self.assertIs(applied['default_member_moderation'], False)
                self.assertEqual(applied['subject_prefix'], '[Splash 2026]')
                calls.send_mail.assert_not_called()

    def test_teachers_list_releases_holds_after_members_added(self):
        """ Held non-member posts are released only after every member is
        added, since a released post goes to the members the list has at
        that moment. """
        for handler_name in ['SectionList', 'ClassList']:
            with self.subTest(handler=handler_name):
                with override_settings(DEFAULT_EMAIL_ADDRESSES=dict(
                        settings.DEFAULT_EMAIL_ADDRESSES,
                        archive='archive@example.com')):
                    calls = self.run_handler(handler_name, 'teachers')
                names = [c[0] for c in calls.mock_calls]
                self.assertEqual(names.count('apply_list_settings'), 2)
                self.assertEqual(names[-1], 'apply_list_settings')
                self.assertEqual(calls.apply_list_settings.call_args_list[-1],
                                 mock.call(calls.apply_list_settings.call_args_list[0][0][0],
                                           {}, release_nonmember_holds=True, errors='log'))
                # Every member in one add_members run, before the release.
                self.assertEqual(names.count('add_list_members'), 1)
                self.assertLess(names.index('add_list_members'), len(names) - 1)
                added = calls.add_list_members.call_args[0][1]
                self.assertIn('archive@example.com', added)
                self.assertIn('director@example.com', added)

    def test_notice_when_password_not_set(self):
        """ If setting the moderator password failed, the notice says so
        rather than giving a wrong password. """
        from django.template.loader import render_to_string
        text = render_to_string('mailman/new_list_intro_teachers.txt',
                                {'classname': 'X', 'mod_password': None})
        self.assertNotIn('None', text)
        self.assertIn("Our website ran into an error setting the list's moderator password. "
                      "Please send us an email and we'll fix this for you.", text)
        # No steps that need the password it doesn't have.
        self.assertNotIn('Enter the password above', text)
        text = render_to_string('mailman/new_list_intro_teachers.txt',
                                {'classname': "Mike's Class", 'mod_password': 'abc123'})
        self.assertIn('abc123', text)
        self.assertIn('Enter the password above', text)
        self.assertNotIn('ran into an error', text)
        # Plain text: no HTML escaping.
        self.assertIn('"Mike\'s Class"', text)

    def test_every_mailman_step_after_create_logs_failures(self):
        """ Once the list is created, every Mailman call setting it up logs
        its failure and lets the setup go on (errors='log'): a list with its
        settings but some members missing beats one with neither, and once the
        list exists later emails go straight to Mailman, so setup is never
        retried. create_list itself raises (see the next test). """
        for handler_name in ['SectionList', 'ClassList']:
            for user_type in ['students', 'teachers']:
                with self.subTest(handler=handler_name, user_type=user_type):
                    calls = self.run_handler(handler_name, user_type)
                    self.assertEqual(calls.mock_calls[0][0], 'create_list')
                    self.assertNotIn('errors', calls.mock_calls[0][2])
                    for name, args, kwargs in calls.mock_calls[1:]:
                        if name != 'send_mail':
                            self.assertEqual(kwargs.get('errors'), 'log', name)

    def test_create_list_failure_stops_setup(self):
        """ Without the list nothing else can work: create_list's failure
        propagates (the mailgate logs it and bounces the email), and nothing
        else runs. """
        from esp.mailman import MailmanError
        for handler_name in ['SectionList', 'ClassList']:
            with self.subTest(handler=handler_name):
                with self.assertRaises(MailmanError):
                    self.run_handler(handler_name, 'teachers',
                                     create_result=MailmanError('newlist S123-teachers: exit status 1'))
                self.assertEqual([c[0] for c in self.last_calls.mock_calls], ['create_list'])

    def test_class_config_file_leaves_nonmember_action_alone(self):
        """ The receivers apply lists/class_mailman.config. If it set
        generic_nonmember_action, it could undo the teachers list's setting
        when both lists are being created at once. """
        import os
        path = os.path.join(settings.PROJECT_ROOT, 'lists/class_mailman.config')
        config = {}
        with open(path) as f:
            exec(f.read(), config)
        self.assertNotIn('generic_nonmember_action', config)


class ProgramListCreationTest(TestCase):
    """ esp.program.views.create_program_lists, run for a new program. """

    def run_create(self, create_result):
        from esp.program import views
        prog = mock.Mock(program_type='Splash', program_instance='2027', url='Splash/2027',
                         director_email='director@example.com')
        with mock.patch.object(views, 'create_list', side_effect=create_result) as create, \
                mock.patch.object(views, 'apply_list_settings') as apply, \
                mock.patch.object(views, 'add_list_members') as add:
            views.create_program_lists(prog)
        return create, apply, add

    def test_new_lists(self):
        from esp.program import views
        with mock.patch.object(views, 'logger') as logger:
            create, apply, add = self.run_create([True, True])
        self.assertEqual([c[0][0] for c in create.call_args_list],
                         ['Splash_2027-students', 'Splash_2027-teachers'])
        self.assertEqual(apply.call_args[1]['listfile'], 'lists/program_mailman.config')
        self.assertEqual(apply.call_count, 2)
        logger.warning.assert_not_called()

    def test_existing_list_warns(self):
        with self.assertLogs('esp.program.views', level='WARNING') as logs:
            create, apply, add = self.run_create([False, True])
        self.assertEqual(len(logs.output), 1)
        self.assertIn('WARNING', logs.output[0])
        self.assertIn('Splash_2027-students already existed', logs.output[0])
        self.assertEqual(apply.call_count, 2)  # set up anyway

    def test_failed_list_skipped(self):
        from esp.mailman import MailmanError
        with self.assertLogs('esp.program.views', level='ERROR'):
            create, apply, add = self.run_create([MailmanError('newlist x: exit status 1'), True])
        self.assertEqual([c[0][0] for c in apply.call_args_list], ['Splash_2027-teachers'])


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

        def fake_popen(args, **popen_kwargs):
            with open(args[2]) as f:
                written['text'] = f.read()
            written['args'] = args
            proc = mock.Mock(returncode=0)
            proc.communicate.return_value = (b'', b'')
            return proc

        with mock.patch.object(mailman, 'Popen', fake_popen):
            result = mailman.apply_list_settings(
                's1-teachers', {'generic_nonmember_action': 0}, **kwargs)
        self.assertIsNone(result)
        self.assertEqual(written['args'][1:2] + written['args'][3:],
                         ['-i', 's1-teachers'])
        return written['text']

    def test_settings_only_by_default(self):
        self.assertEqual(self.written_config(),
                         'generic_nonmember_action = 0\n')

    def test_listfile_first(self):
        """ A list-settings file goes first, so 'data' overrides it. """
        import os
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.config', delete=False) as f:
            f.write('generic_nonmember_action = 1\nsubject_prefix = "x"')
        self.addCleanup(os.unlink, f.name)
        self.assertEqual(self.written_config(listfile=f.name),
                         'generic_nonmember_action = 1\nsubject_prefix = "x"\n'
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


def load_mailman_module():
    """ A copy of esp.mailman with USE_MAILMAN on. Its functions become no-ops
    at import time unless USE_MAILMAN is on. """
    import importlib.util
    import esp.mailman
    spec = importlib.util.spec_from_file_location(
        'esp_mailman_under_test', esp.mailman.__file__)
    mailman = importlib.util.module_from_spec(spec)
    with override_settings(USE_MAILMAN=True, MAILMAN_PATH='/fake/',
                           MAILMAN_PASSWORD='secret-admin-pw'):
        spec.loader.exec_module(mailman)
    return mailman


class MailmanCheckTest(TestCase):
    """ esp.mailman's functions raise MailmanError when a command fails:
    Mailman's commands report some failures only by exit status and some only
    in their output. errors='log' / 'ignore' turn that into a log line or
    nothing. """

    def setUp(self):
        self.mailman = load_mailman_module()

    def run_with(self, returncode, output, func, *args, **kwargs):
        proc = mock.Mock(returncode=returncode)
        proc.communicate.return_value = (output.encode(), b'')
        with mock.patch.object(self.mailman, 'Popen', return_value=proc) as popen:
            result = func(*args, **kwargs)
        return result, popen

    def test_exit_status_raises_without_arguments(self):
        with self.assertRaises(self.mailman.MailmanError) as cm:
            self.run_with(1, 'Illegal list name: x', self.mailman.create_list,
                          's1-teachers', 'owner@example.com')
        self.assertIn('newlist s1-teachers', str(cm.exception))
        self.assertIn('Illegal list name', str(cm.exception))
        # newlist's arguments include the list admin password.
        self.assertNotIn('secret-admin-pw', str(cm.exception))

    def test_list_already_exists_is_fine(self):
        """ esp-web's SSH wrapper hides newlist's "List already exists", so
        create_list checks whether the list is there. """
        failed, exists = mock.Mock(returncode=1), mock.Mock(returncode=0)
        failed.communicate.return_value = (b'command failed: Process exited with: 1.', b'')
        exists.communicate.return_value = (b'a@example.com', b'')
        with mock.patch.object(self.mailman, 'Popen', side_effect=[failed, exists]) as popen:
            self.assertIs(self.mailman.create_list('s1-teachers', 'owner@example.com'), False)
        self.assertEqual([c[0][0][0].rsplit('/', 1)[-1] for c in popen.call_args_list],
                         ['newlist', 'list_members'])

    def test_add_members_refused_address_raises(self):
        with self.assertRaises(self.mailman.MailmanError) as cm:
            self.run_with(0, 'Subscribed: a@example.com\nBad/Invalid email address: blank line',
                          self.mailman.add_list_members, 's1-teachers',
                          ['a@example.com', ''])
        self.assertIn('Bad/Invalid email address: blank line', str(cm.exception))

    def test_add_members_ok(self):
        result, popen = self.run_with(
            0, 'Subscribed: a@example.com\nAlready a member: b@example.com',
            self.mailman.add_list_members, 's1-teachers',
            ['a@example.com', 'b@example.com'])
        self.assertEqual(popen.call_args[0][0][-1], 's1-teachers')

    def test_no_such_list_raises(self):
        with self.assertRaises(self.mailman.MailmanError):
            self.run_with(1, 'No such list: s1-teachers',
                          self.mailman.add_list_members, 's1-teachers',
                          ['a@example.com'])

    def test_config_list_problems_in_output_raise(self):
        for output in ['could not release held message 3: oops']:
            with self.subTest(output=output):
                with self.assertRaises(self.mailman.MailmanError):
                    self.run_with(0, output, self.mailman.apply_list_settings,
                                  's1-teachers', {'subject_prefix': 'x'})

    def test_remove_members_cant_open_list_raises(self):
        with self.assertRaises(self.mailman.MailmanError):
            self.run_with(0, 'Error opening list s1-teachers... skipping.',
                          self.mailman.remove_list_member, 's1-teachers',
                          ['a@example.com'])
        result, _ = self.run_with(0, 'No such member: a@example.com',
                                  self.mailman.remove_list_member, 's1-teachers',
                                  ['a@example.com'])

    def test_all_lists_check(self):
        result, _ = self.run_with(0, 'a-teachers\nb-students', self.mailman.all_lists,
                                  show_nonpublic=True)
        self.assertEqual(result, ['a-teachers', 'b-students'])
        with self.assertRaises(self.mailman.MailmanError):
            self.run_with(255, 'ssh: connect to host esp-mail: timed out',
                          self.mailman.all_lists)

    def test_create_list_returns_true_when_created(self):
        self.assertIs(self.run_with(0, '', self.mailman.create_list, 's1-teachers',
                                    'owner@example.com')[0], True)

    def test_command_that_cant_start(self):
        """ A command that can't even be started (no such program, no ssh)
        is a MailmanError too, so errors='log' / 'ignore' cover it. """
        with mock.patch.object(self.mailman, 'Popen',
                               side_effect=FileNotFoundError(2, 'No such file or directory')):
            with self.assertRaises(self.mailman.MailmanError) as cm:
                self.mailman.existing_lists()
            self.assertIn('ls (all lists): could not run: No such file or directory', str(cm.exception))
            self.assertEqual(self.mailman.existing_lists(errors='ignore'), set())
            with self.assertLogs(self.mailman.logger, level='ERROR'):
                self.assertIsNone(self.mailman.add_list_member('s1-students', 'a@example.com',
                                                               errors='log'))

    def test_none_address_skipped(self):
        self.assertEqual(self.mailman._addresses([None, 'a@example.com'], formatted=False),
                         ['a@example.com'])

    def test_timeout(self):
        from subprocess import TimeoutExpired
        proc = mock.Mock(returncode=None)
        proc.communicate.side_effect = [TimeoutExpired('ssh', 30), (b'', b'')]
        with mock.patch.object(self.mailman, 'Popen', return_value=proc), \
                self.assertRaises(self.mailman.MailmanError) as cm:
            self.mailman.list_contents('s1-students')
        self.assertIn('list_members s1-students: no answer after 30 s', str(cm.exception))
        proc.kill.assert_called_once_with()
        self.assertEqual(proc.communicate.call_args_list[0][1], {'timeout': 30})

    def test_existing_lists(self):
        result, popen = self.run_with(0, 'A-teachers\nb-students\n', self.mailman.existing_lists)
        self.assertEqual(result, {'a-teachers', 'b-students'})
        self.assertEqual(popen.call_args[0][0][-2:], ['-1', '/var/lib/mailman/lists'])
        self.assertEqual(self.run_with(1, 'command failed', self.mailman.existing_lists,
                                       errors='ignore')[0], set())

    def test_sync_list_members(self):
        """ One read, one remove of the extra members (but not 'keep'), one
        add of the missing ones; addresses compare case-insensitively. """
        new = ESPUser(username='new', email='New@example.com', first_name='N', last_name='U')
        stays = ESPUser(username='stays', email='stays@example.com')
        current = 'Stays@example.com\nold@example.com\nDirector@example.com'
        result, popen = self.run_with(0, current, self.mailman.sync_list_members, 's1-students',
                                      [new, stays, 'new@example.com', ''],
                                      keep=['director@example.com', None])
        commands = [c[0][0][0].rsplit('/', 1)[-1] for c in popen.call_args_list]
        self.assertEqual(commands, ['list_members', 'remove_members', 'add_members'])
        inputs = [c[1].get('input', c[0][0] if c[0] else None)
                  for c in popen.return_value.communicate.call_args_list]
        self.assertEqual(inputs[1], b'old@example.com')
        self.assertEqual(inputs[2].count(b'@'), 1)
        self.assertIn(b'New@example.com', inputs[2])

    def test_sync_list_members_nothing_to_change(self):
        result, popen = self.run_with(0, 'a@example.com', self.mailman.sync_list_members,
                                      's1-students', ['A@example.com'])
        self.assertEqual(popen.call_count, 1)

    def test_errors_log(self):
        """ errors='log' logs the failure and returns None (changes) or []
        (reads); other exceptions still propagate. """
        with self.assertLogs(self.mailman.logger, level='ERROR') as logs:
            result, _ = self.run_with(1, 'No such list: s1-teachers',
                                      self.mailman.add_list_members, 's1-teachers',
                                      ['a@example.com'], errors='log')
        self.assertIsNone(result)
        self.assertIn('add_members s1-teachers', logs.output[0])
        with self.assertLogs(self.mailman.logger, level='ERROR'):
            result, _ = self.run_with(1, 'No such list: s1-students',
                                      self.mailman.list_contents, 's1-students', errors='log')
        self.assertEqual(result, [])
        with self.assertLogs(self.mailman.logger, level='ERROR'):
            result, _ = self.run_with(1, 'x', self.mailman.set_list_moderator_password,
                                      's1-students', errors='log')
        self.assertIsNone(result)
        # (A command that can't start is a MailmanError: test_command_that_cant_start.)
        with mock.patch.object(self.mailman, 'Popen', side_effect=ValueError('bug')):
            with self.assertRaises(ValueError):
                self.mailman.create_list('s1-teachers', 'o@example.com', errors='log')

    def test_errors_log_traceback_includes_caller(self):
        """ The logged failure carries a traceback from the code that called
        the Mailman function down to the failed command, so its Bugsink issue
        shows who ran it. """
        def some_caller():
            return self.run_with(1, 'No such list: s1-teachers',
                                 self.mailman.add_list_member, 's1-teachers',
                                 'a@example.com', errors='log')[0]
        with self.assertLogs(self.mailman.logger, level='ERROR') as logs:
            self.assertIsNone(some_caller())
        exc_type, exc, tb = logs.records[0].exc_info
        self.assertIs(exc_type, self.mailman.MailmanError)
        functions = [frame.name for frame in traceback.extract_tb(tb)]
        # Outermost first: this test, its caller, ..., the Mailman function's
        # wrapper, where it was caught; not the frames inside it.
        self.assertIn('test_errors_log_traceback_includes_caller', functions)
        self.assertEqual(functions[-1], 'wrapper')
        self.assertNotIn('_run_checked', functions)
        self.assertIn('some_caller', logs.output[0])  # in the log file's traceback too

    def test_errors_log_traceback_has_no_password(self):
        """ Bugsink gets each logged frame's local variables; none may hold
        the list admin password (newlist's arguments). create_list's failure
        is raised while handling its failed "does the list exist?" check, so
        it comes chained to that one, whose frames hold the password too. """
        with self.assertLogs(self.mailman.logger, level='ERROR') as logs:
            self.run_with(1, 'command failed', self.mailman.create_list,
                          's1-teachers', 'owner@example.com', errors='log')
        exc, tb = logs.records[0].exc_info[1:]
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(exc.__context__)
        self.assertIs(exc.__traceback__, tb)
        while tb is not None:
            self.assertNotIn('secret-admin-pw', repr(tb.tb_frame.f_locals),
                             tb.tb_frame.f_code.co_name)
            tb = tb.tb_next

    def test_errors_ignore(self):
        """ errors='ignore' returns the same as 'log', without logging. """
        with mock.patch.object(self.mailman.logger, 'error') as error:
            result, _ = self.run_with(1, 'No such list: s1-students',
                                      self.mailman.list_contents, 's1-students', errors='ignore')
            self.assertEqual(result, [])
            result, _ = self.run_with(1, 'No such list: s1-students',
                                      self.mailman.add_list_member, 's1-students',
                                      'a@example.com', errors='ignore')
            self.assertIsNone(result)
        error.assert_not_called()

    def test_errors_value_checked(self):
        with self.assertRaises(ValueError):
            self.mailman.create_list('s1-teachers', 'o@example.com', errors='warn')

    def test_set_password_returns_it(self):
        result, _ = self.run_with(0, '', self.mailman.set_list_moderator_password,
                                  's1-students', password='abc123')
        self.assertEqual(result, 'abc123')

    def test_lists_containing_returns_list_names_only(self):
        """ find_member's "<addr> found in:" header lines aren't lists. """
        result, _ = self.run_with(
            0, 'a@example.com found in:\n     s1-students\n     splash_2026-teachers (as owner)\n'
               'A@example.com found in:\n     announcements',
            self.mailman.lists_containing, 'a@example.com')
        # A list it only owns isn't one it's a member of.
        self.assertEqual(result, ['announcements', 's1-students'])

    SSH = {'host': 'mailhost', 'user': 'espweb', 'key': '/k/id_rsa',
           'known_hosts': '/k/known_hosts', 'control_dir': '/tmp/mm-test-cm',
           'options': ['PubkeyAcceptedAlgorithms=+ssh-rsa']}

    def test_ssh_argv_quotes_every_argument(self):
        """ The remote shell parses the command line: arguments must reach
        Mailman as they are, not run as shell code. """
        import shlex
        with override_settings(MAILMAN_SSH=self.SSH):
            _, popen = self.run_with(0, '', self.mailman.lists_containing,
                                     'x&touch /tmp/pwned&$(id)`id`@a.co')
        argv = popen.call_args[0][0]
        self.assertEqual(argv[0], 'ssh')
        self.assertEqual(argv[argv.index('-i') + 1], '/k/id_rsa')
        options = [argv[i + 1] for i, a in enumerate(argv) if a == '-o']
        for option in ['BatchMode=yes', 'StrictHostKeyChecking=yes', 'ControlMaster=auto',
                       'ControlPath=/tmp/mm-test-cm/%C', 'ControlPersist=30',
                       'UserKnownHostsFile=/k/known_hosts', 'PubkeyAcceptedAlgorithms=+ssh-rsa']:
            self.assertIn(option, options)
        self.assertEqual(argv[-2], 'espweb@mailhost')
        # What the remote shell runs, word by word:
        self.assertEqual(shlex.split(argv[-1]),
                         ['sudo', 'find_member',
                          '^(%s)$' % re_escape('x&touch /tmp/pwned&$(id)`id`@a.co')])

    def test_ssh_config_list_on_stdin(self):
        """ Over SSH, config_list reads its settings from stdin (no file to
        copy over). """
        import shlex
        proc = mock.Mock(returncode=0)
        proc.communicate.return_value = (b'', b'')
        with override_settings(MAILMAN_SSH=self.SSH), \
                mock.patch.object(self.mailman, 'Popen', return_value=proc) as popen:
            self.mailman.apply_list_settings('s1-teachers', {'subject_prefix': '[x] '})
        self.assertEqual(shlex.split(popen.call_args[0][0][-1]),
                         ['sudo', 'config_list', '-i', '/dev/stdin', 's1-teachers'])
        self.assertEqual(proc.communicate.call_args[0][0], b"subject_prefix = '[x] '\n")

    def test_without_ssh_runs_mailman_path(self):
        _, popen = self.run_with(0, '', self.mailman.list_contents, 's1-students')
        self.assertEqual(popen.call_args[0][0], ['/fake/list_members', 's1-students'])

    def test_blank_addresses_skipped(self):
        """ Blank addresses (a user with no email, an empty or whitespace
        string) are left out; with none left, Mailman isn't called. """
        from esp.users.models import ESPUser
        no_email = ESPUser(username='noemail', email='')
        has_email = ESPUser(username='t1', first_name='T', last_name='One', email='t1@example.com')
        for func in (self.mailman.add_list_members, self.mailman.remove_list_member):
            with self.subTest(func=func.__name__):
                result, popen = self.run_with(0, '', func, 's1-teachers', [no_email, '', '  '])
                popen.assert_not_called()
                proc = mock.Mock(returncode=0)
                proc.communicate.return_value = (b'', b'')
                with mock.patch.object(self.mailman, 'Popen', return_value=proc):
                    func('s1-teachers', [no_email, has_email, ' a@example.com ', ''])
                proc_input = proc.communicate.call_args[0][0].decode('iso-8859-1')
                self.assertEqual(len(proc_input.split('\n')), 2, proc_input)
                self.assertIn('t1@example.com', proc_input)
                self.assertIn('a@example.com', proc_input)
        for member in (no_email, '', ' '):
            with self.subTest(member=member):
                _, popen = self.run_with(0, '', self.mailman.add_list_member, 's1-teachers', member)
                popen.assert_not_called()
                _, popen = self.run_with(0, '', self.mailman.remove_list_member, 's1-teachers', member)
                popen.assert_not_called()

    def test_lists_containing_regex_and_blanks(self):
        """ The address is escaped (a+b must match itself); a blank address
        searches nothing; a user with no email is found by username. """
        from esp.users.models import ESPUser
        _, popen = self.run_with(0, '', self.mailman.lists_containing, 'a+b@x.com')
        self.assertEqual(popen.call_args[0][0][-1], r'^(a\+b@x\.com)$')
        result, popen = self.run_with(0, '', self.mailman.lists_containing, ' ')
        self.assertEqual(result, [])
        popen.assert_not_called()
        _, popen = self.run_with(0, '', self.mailman.lists_containing,
                                 ESPUser(username='noemail', email=''))
        self.assertEqual(popen.call_args[0][0][-1], r'^(noemail@esp\.mit\.edu)$')

    def test_list_contents_missing_list_raises_empty_list_doesnt(self):
        """ A list that can't be read is an error, not an empty list. """
        with self.assertRaises(self.mailman.MailmanError):
            self.run_with(1, 'No such list: s1-students', self.mailman.list_contents, 's1-students')
        result, _ = self.run_with(0, '', self.mailman.list_contents, 's1-students')
        self.assertEqual(result, [])
        result, _ = self.run_with(0, 'a@example.com\nb@example.com', self.mailman.list_contents, 's1-students')
        self.assertEqual(result, ['a@example.com', 'b@example.com'])


class ClassTeachersListSyncTest(TestCase):
    """ esp.program.models.class_: when a class's teachers change, its
    existing mailing lists (teachers, students, class) follow. """

    def make_class(self):
        cls = mock.Mock()
        cls.id = 123
        cls.emailcode.return_value = 'S123'
        sections = []
        for i in (1, 2):
            sec = mock.Mock()
            sec.emailcode.return_value = 'S123s%d' % i
            sections.append(sec)
        cls.sections.all.return_value = sections
        cls.parent_program.director_email = 'Director@example.com'
        cls.teachers.values_list.return_value = []  # the teachers after the change
        return cls

    def user(self, email):
        u = mock.Mock()
        u.email = email
        return u

    def sync(self, existing, teachers=(), **kwargs):
        from esp.program.models import class_
        calls = []

        def record(name):
            def fake(*args, **kwargs):
                self.assertEqual(kwargs, {'errors': 'log'})
                calls.append((name, args))
            return fake
        with mock.patch.object(class_, 'existing_lists', return_value=set(existing)) as lists, \
                mock.patch.object(class_, 'add_list_members', side_effect=record('add_list_members')), \
                mock.patch.object(class_, 'remove_list_member', side_effect=record('remove_list_member')):
            with override_settings(DEFAULT_EMAIL_ADDRESSES=dict(
                    settings.DEFAULT_EMAIL_ADDRESSES, archive='archive@example.com')):
                cls = self.make_class()
                cls.teachers.values_list.return_value = list(teachers)
                class_.sync_class_teachers_lists(cls, **kwargs)
        if kwargs.get('added') or kwargs.get('removed'):
            self.assertEqual(lists.call_args, mock.call(errors='log'))
        return calls

    def test_only_existing_lists(self):
        t = self.user('t@example.com')
        # Teachers are members of every list a class (or section) has.
        calls = self.sync(['s123-teachers', 's123s2-teachers', 's123-students', 's123s1-class',
                           's1234-teachers', 's12-students', 'other'],
                          added=[t])
        self.assertEqual([(name, a[0]) for name, a in calls],
                         [('add_list_members', 's123-teachers'),
                          ('add_list_members', 's123-students'),
                          ('add_list_members', 's123s1-class'),
                          ('add_list_members', 's123s2-teachers')])
        self.assertEqual(calls[0][1][1], [t])

    def test_list_lists_failure_means_no_calls(self):
        """ existing_lists(errors='log') returns an empty set after logging a failure. """
        self.assertEqual(self.sync([], added=[self.user('t@example.com')]), [])

    def test_no_lists_no_calls(self):
        self.assertEqual(self.sync(['s1234-students', 's12-class', 'other'],
                                   added=[self.user('t@example.com')]), [])

    def test_remove_keeps_director_and_archive(self):
        calls = self.sync(['s123-teachers'], removed=[
            self.user('t@example.com'), self.user('director@example.com'),
            self.user('archive@example.com'), self.user('')])
        self.assertEqual(calls, [('remove_list_member', ('s123-teachers', ['t@example.com']))])

    def test_remove_keeps_address_a_remaining_teacher_has(self):
        """ Two accounts with one email: removing one keeps the address. """
        calls = self.sync(['s123-teachers'], teachers=['Shared@example.com', None],
                          removed=[self.user('shared@example.com'), self.user('t@example.com')])
        self.assertEqual(calls, [('remove_list_member', ('s123-teachers', ['t@example.com']))])

    def test_existing_lists_passed_in(self):
        """ With 'existing' given, no existing_lists call. """
        from esp.program.models import class_
        with mock.patch.object(class_, 'existing_lists') as lists, \
                mock.patch.object(class_, 'add_list_members') as add:
            class_.sync_class_teachers_lists(self.make_class(), added=[self.user('t@example.com')],
                                             existing={'s123s1-teachers'})
        lists.assert_not_called()
        self.assertEqual(add.call_args[0][0], 's123s1-teachers')

    def test_signal_after_commit(self):
        """ The signal syncs only once the change is committed, and maps the
        changed users to the class. """
        from esp.program.models import class_
        cls = self.make_class()
        users = [self.user('t@example.com')]
        pending = []
        with override_settings(USE_MAILMAN=True), \
                mock.patch.object(class_.transaction, 'on_commit', pending.append), \
                mock.patch.object(class_.ESPUser.objects, 'filter', return_value=users), \
                mock.patch.object(class_, '_existing_list_names', return_value={'x'}), \
                mock.patch.object(class_, 'sync_class_teachers_lists') as sync:
            class_._class_teachers_changed(None, instance=cls, action='post_add',
                                           reverse=False, pk_set={5})
            sync.assert_not_called()
            self.assertEqual(len(pending), 1)
            pending[0]()
        sync.assert_called_once_with(cls, added=users, existing={'x'})

    def test_signal_reverse_lists_mailman_lists_once(self):
        """ One user removed from several classes: one list_lists call. """
        from esp.program.models import class_
        classes = [self.make_class(), self.make_class()]
        pending = []
        with override_settings(USE_MAILMAN=True), \
                mock.patch.object(class_.transaction, 'on_commit', pending.append), \
                mock.patch.object(class_.ClassSubject.objects, 'filter', return_value=classes), \
                mock.patch.object(class_, '_existing_list_names', return_value={'x'}) as names, \
                mock.patch.object(class_, 'sync_class_teachers_lists') as sync:
            user = self.user('t@example.com')
            class_._class_teachers_changed(None, instance=user, action='post_remove',
                                           reverse=True, pk_set={1, 2})
            pending[0]()
        names.assert_called_once_with()
        self.assertEqual(sync.call_args_list,
                         [mock.call(c, removed=[user], existing={'x'}) for c in classes])

    def test_signal_off_without_mailman(self):
        from esp.program.models import class_
        with override_settings(USE_MAILMAN=False), \
                mock.patch.object(class_.transaction, 'on_commit') as on_commit:
            class_._class_teachers_changed(None, instance=self.make_class(),
                                           action='post_add', reverse=False, pk_set={5})
        on_commit.assert_not_called()

    def test_signal_sync_errors_are_logged(self):
        from esp.program.models import class_
        pending = []
        with override_settings(USE_MAILMAN=True), \
                mock.patch.object(class_.transaction, 'on_commit', pending.append), \
                mock.patch.object(class_.ESPUser.objects, 'filter', return_value=[]), \
                mock.patch.object(class_, '_existing_list_names', return_value=set()), \
                mock.patch.object(class_, 'sync_class_teachers_lists', side_effect=RuntimeError('x')):
            class_._class_teachers_changed(None, instance=self.make_class(),
                                           action='post_remove', reverse=False, pk_set={5})
            with self.assertLogs(class_.logger, level='ERROR'):
                pending[0]()


class MailmanListPickerTest(TestCase):
    """ The comm panel's Mailman list picker (esp.users.views.usersearch) says
    when Mailman can't be read, rather than showing what looks like no lists. """

    def picker_context(self, **all_lists_kwargs):
        from esp.users.views import usersearch
        with mock.patch('esp.mailman.all_lists', **all_lists_kwargs), \
                mock.patch.object(usersearch, 'render_to_response') as render, \
                self.assertLogs(usersearch.logger, level='ERROR') if 'side_effect' in all_lists_kwargs \
                else mock.patch.object(usersearch, 'logger'):
            usersearch._mailman_list_picker(mock.Mock())
        return render.call_args[0][2]

    def test_mailman_failure_shown(self):
        from esp.mailman import MailmanError
        context = self.picker_context(side_effect=MailmanError('list_lists: exit status 255: x'))
        self.assertIn("Couldn't read the mailing lists", context['mailman_error'])
        self.assertEqual(context['public_lists'], [])

    def test_lists_shown(self):
        context = self.picker_context(return_value=['a-teachers'])
        self.assertIsNone(context['mailman_error'])
        self.assertEqual(context['public_lists'], ['a-teachers'])
